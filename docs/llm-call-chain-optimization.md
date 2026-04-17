# LLM 调用链优化文档

> 生成日期：2026-04-16  
> 范围：`Backend/` 中所有 LLM 调用路径

---

## 1. 调用链现状总览

### 1.1 LLM 调用点清单

| # | 触发入口 | 用例 / 技能 | LLM 方法 | 调用模式 | 并发控制 | 重试机制 |
|---|---------|------------|---------|---------|---------|---------|
| 1 | `POST /api/chat`（普通问答） | `ChatUseCase.execute()` | `stream_chat()` | 同步流式 | 无 | 无 |
| 2 | `POST /api/chat`（故障树解说） | `ChatUseCase.execute()` | `stream_chat()` | 同步流式（前台） | 无 | 无 |
| 3 | `POST /api/chat`（故障树生成/修改） | `FaultTreeSkill` → `chat_with_tools()` | `chat_with_tools()` | 异步线程（后台） | 无 | 无 |
| 4 | `POST /api/files`（文件上传） | `ImportFileUseCase` → `TripleExtractor.batch_extract()` → `GraphExtractionSkill.extract()` | `stream_chat()` × N | 线程池并发 | `max_workers=50` | 无（单 chunk 失败跳过） |
| 5 | `PUT /api/fault-trees/:id` | `ExpertLearningUseCase._learn_from_fault_tree()` | `stream_chat()` | daemon 线程 | 无 | 无 |
| 6 | `PUT /api/fault-trees/:id` | `ExpertLearningUseCase` → `GraphExtractionSkill.extract()` | `stream_chat()` | daemon 线程内同步 | 无 | 无 |

### 1.2 并发线程模型

```
请求线程
├── ChatUseCase.execute()
│   ├── [前台] stream_chat() → SSE 推送
│   └── [后台 daemon] chat_with_tools() → FaultTreeSkill
│       └── threading.Event 等待，超时 120s
│
├── ImportFileUseCase.embed_file()           ← FileEndpoint daemon 线程
│   └── ThreadPoolExecutor(max_workers=50)
│       └── GraphExtractionSkill.extract() × N
│
└── ExpertLearningUseCase
    ├── learn_from_fault_tree_async()        ← daemon 线程
    │   ├── stream_chat()                    (学习报告)
    │   └── GraphExtractionSkill.extract()   (三元组)
    └── index_conversation_round()           ← daemon 线程（不调 LLM）
```

---

## 2. 已识别问题

### P1：无 LLM 重试与降级

**现状**：`LLMService` 的 `stream_chat()` 和 `chat_with_tools()` 均无重试逻辑。任何网络抖动、API 限流或超时都会直接抛异常。

**影响范围**：所有 6 个调用点。

**风险**：
- DeepSeek API 偶发 502/503/429 导致对话中断
- 大文件上传时批量三元组抽取，50 个并发线程同时请求，极易触发 API 限流
- 专家修改学习在 daemon 线程中失败后完全静默丢失

### P2：三元组抽取并发度过高且无限流

**现状**：`TripleExtractor.batch_extract()` 使用 `ThreadPoolExecutor(max_workers=50)` 并发调用 LLM，仅靠 `time.sleep(0.1)` 作为请求间隔。

**影响**：
- 50 个线程几乎同时启动，瞬时并发远超常见 API 速率限制（DeepSeek 通常 10-60 RPM）
- `sleep(0.1)` 位于 `_extract_from_merged` 的**末尾**，首批 50 个请求无任何间隔
- 大文件（100+ chunk → 50+ 合并组）可在秒级内发出 50 个请求

### P3：daemon 线程无生命周期管理

**现状**：`ExpertLearningUseCase`、`FileEndpoint`、`ChatUseCase` 共 4 处使用 `daemon=True` 的裸线程。

**影响**：
- 进程退出时 daemon 线程被强制终止，可能写入不完整数据
- 无法追踪正在运行的后台任务数量
- 无法对同一故障树的重复修改进行去重或排队

### P4：LLM 调用缺少 token 预算控制

**现状**：`LLMService` 创建时 `temperature=0.7`，未设置 `max_tokens`。Prompt 长度无上限控制。

**影响**：
- 故障树场景（修改前 + 修改后快照 + 变更摘要 + 对话上下文）可能组装出超长 prompt
- 20 轮对话历史 + GraphRAG 上下文 + 文档片段同时注入，token 消耗无封顶
- 输出无 `max_tokens` 约束，可能生成过长回复导致延迟

### P5：LLM 实例未复用配置差异化

**现状**：全局单一 `LLMService` 实例，所有场景共用 `temperature=0.7`。

**影响**：
- 三元组抽取是结构化 JSON 输出，需要低 temperature（0.0-0.2）以保证格式稳定
- 故障树 Function Calling 也需要确定性输出
- 普通对话和专家报告可以用较高 temperature 保持创造性

### P6：向量库写入无批量优化

**现状**：`_upsert_graph_vectors()` 和 `_build_graph()` 逐条写入 entity/relation 到 ChromaDB。

**影响**：
- N 条三元组产生 ~2N 次 `add_entity()` + N 次 `add_relation()` 调用
- ChromaDB 的 `add()` 每次调用有固定开销（磁盘 fsync）

### P7：缺少可观测性指标

**现状**：仅有 `logger.info` / `logger.exception`，无结构化指标。

**影响**：
- 无法统计每条调用链的 LLM 耗时、token 消耗、成功率
- 无法在生产环境监控 API 费用和性能瓶颈
- 故障排查只能翻日志

---

## 3. 优化建议

### 3.1 【高优先级】为 LLMService 添加重试与限流

**目标**：解决 P1 + P2

```python
# 方案：在 LLMService.__init__ 中配置 langchain 的内置重试
from langchain_openai import ChatOpenAI

self._llm = ChatOpenAI(
    model=model,
    api_key=api_key,
    base_url=base_url,
    temperature=temperature,
    streaming=True,
    max_retries=3,           # ← 新增：自动重试 3 次（指数退避）
    request_timeout=60,      # ← 新增：单次请求超时 60s
)
```

**对 TripleExtractor 的补充**：降低 `max_workers` 并改用信号量控制并发：

```python
ASYNC_TRIPLE_EXTRACT_MAX_WORKERS = 5   # 从 50 降到 5
REQUEST_INTERVAL = 1.0                  # 从 0.1 升到 1.0

# 或引入 threading.Semaphore 在全局层面限制并发 LLM 调用
```

**预期收益**：
- API 偶发错误自动恢复，用户无感知
- 大文件上传不再触发限流雪崩

---

### 3.2 【高优先级】按场景差异化 LLM 配置

**目标**：解决 P5

```python
# app_factory.py 中创建多个 LLMService 实例
llm_chat = LLMService(temperature=0.7)                    # 对话
llm_structured = LLMService(temperature=0.0, max_tokens=2048)  # 三元组 / Function Calling
llm_report = LLMService(temperature=0.3, max_tokens=4096)      # 专家学习报告

# 注入到不同用例
chat_use_case = ChatUseCase(llm_service=llm_chat, ...)
triple_extractor = TripleExtractor(llm_service=llm_structured, ...)
expert_learning = ExpertLearningUseCase(llm_service=llm_report, ...)
```

**预期收益**：
- 三元组抽取 JSON 解析失败率显著降低
- Function Calling 稳定性提升
- 各场景可独立调优参数

---

### 3.3 【中优先级】统一后台任务管理器

**目标**：解决 P3

```python
# Backend/Infrastructure/task/BackgroundTaskManager.py
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    def __init__(self, max_workers: int = 3):
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="bg-task",
        )
        self._futures: dict[str, Future] = {}

    def submit(self, task_id: str, fn, *args, **kwargs):
        if task_id in self._futures and not self._futures[task_id].done():
            logger.info("任务 %s 已在执行中，跳过重复提交", task_id)
            return
        future = self._executor.submit(fn, *args, **kwargs)
        self._futures[task_id] = future
        future.add_done_callback(lambda f: self._on_done(task_id, f))

    def _on_done(self, task_id: str, future):
        if future.exception():
            logger.exception("后台任务失败: %s", task_id, exc_info=future.exception())

    def shutdown(self, wait: bool = True):
        self._executor.shutdown(wait=wait)
```

**改造点**：
- `ExpertLearningUseCase` 中 2 处 `threading.Thread(daemon=True)` → `task_manager.submit()`
- `FileEndpoint` 中 1 处 `threading.Thread(daemon=True)` → `task_manager.submit()`
- `ChatUseCase` 中故障树后台线程 → `task_manager.submit()`
- Flask app 关闭时调用 `task_manager.shutdown(wait=True)` 确保数据写完

**预期收益**：
- 防止同一故障树的连续修改产生竞态
- 优雅关停，不丢数据
- 可查询后台任务状态

---

### 3.4 【中优先级】添加 Prompt Token 预算控制

**目标**：解决 P4

在 `ContextManager` 已有 token 预算机制的基础上，对其他未经过 ContextManager 的路径也加防护：

```python
# ExpertLearningUseCase — 截断过长快照
MAX_SNAPSHOT_CHARS = 8000  # 约 2000 token

def _render_tree_snapshot(self, tree_snapshot: dict) -> str:
    text = ...  # 现有逻辑
    if len(text) > MAX_SNAPSHOT_CHARS:
        text = text[:MAX_SNAPSHOT_CHARS] + "\n...(已截断)"
    return text
```

```python
# LLMService — 添加全局 max_tokens 参数
class LLMService(ILLMService):
    def __init__(self, ..., max_tokens: int | None = None):
        kwargs = {...}
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        self._llm = ChatOpenAI(**kwargs)
```

**预期收益**：
- 避免意外超长 prompt 导致 API 报错或高额费用
- 输出长度可控，降低流式延迟

---

### 3.5 【中优先级】向量库批量写入

**目标**：解决 P6

```python
# 将逐条写入改为批量
def _upsert_graph_vectors(self, triples: list, source_file: str) -> None:
    entities = []
    relations = []
    seen = set()
    for t in triples:
        for name, etype in [(t.head, t.head_type), (t.tail, t.tail_type)]:
            if name and name not in seen:
                entities.append((name, etype))
                seen.add(name)
        if t.head and t.relation and t.tail:
            relations.append((t.head, t.relation, t.tail))

    # 批量接口（需 ChromaVectorStoreRepository 新增 batch 方法）
    self._vector_store.batch_add_entities(entities, source_file=source_file)
    self._vector_store.batch_add_relations(relations, source_file=source_file)
```

**预期收益**：
- ChromaDB 写入次数从 ~3N 降至 2 次
- 大文件图谱构建耗时显著降低

---

### 3.6 【低优先级】添加可观测性埋点

**目标**：解决 P7

```python
# 在 LLMService 中包装计时 + token 统计
import time

def stream_chat(self, messages: list[dict]) -> Generator[str, None, None]:
    start = time.perf_counter()
    token_count = 0
    try:
        for chunk in self._llm.stream(lc_messages):
            if chunk.content:
                token_count += 1  # 粗略计数
                yield chunk.content
    finally:
        elapsed = time.perf_counter() - start
        logger.info(
            "LLM stream_chat: %.2fs, ~%d output tokens",
            elapsed, token_count,
        )
```

更进一步可引入 `prometheus_client` 暴露：
- `llm_request_duration_seconds`（直方图，按 caller 标签分）
- `llm_request_total`（计数器，按 status=success/error 分）
- `llm_tokens_total`（计数器，按 direction=input/output 分）

---

## 4. 优化优先级路线图

```
阶段一（立即可做，改动小）
 ├─ 3.1  LLMService 添加 max_retries + request_timeout
 ├─ 3.1  TripleExtractor max_workers 50 → 5
 └─ 3.2  按场景差异化 temperature

阶段二（短期，需新增组件）
 ├─ 3.3  BackgroundTaskManager 替换裸 daemon 线程
 ├─ 3.4  Prompt token 截断保护
 └─ 3.6  LLMService 计时日志

阶段三（中期，需接口变更）
 ├─ 3.5  ChromaDB batch 写入接口
 └─ 3.6  Prometheus 指标暴露
```

---

## 5. 关键指标对比（预期）

| 指标 | 当前 | 优化后 |
|------|------|--------|
| 三元组抽取并发数 | 50 线程瞬时 | 5 线程 + 信号量 |
| API 限流失败率（大文件） | 高 | 极低（自动重试 + 限流） |
| LLM 偶发 5xx 恢复 | 用户手动重试 | 自动 3 次指数退避 |
| daemon 线程数据丢失风险 | 进程退出即丢 | 优雅关停等待完成 |
| 三元组 JSON 解析失败率 | ~10-15%（temperature=0.7） | ~2-3%（temperature=0.0） |
| ChromaDB 图谱写入次数/100 三元组 | ~300 次 | 2 次 |
| 可观测性 | 纯日志 | 结构化指标 + 日志 |
