# 轻量级 GraphRAG 工程化落地指南
> 适用场景：Python + Flask + ChromaDB，硬件资源受限环境
> 参考方向：LightRAG、PathRAG、HippoRAG、Query-Driven GraphRAG（2024–2025）

---

## 一、核心思路与架构总览

### 设计原则

| 原则 | 说明 |
|------|------|
| **拒绝全局重型图谱** | 不使用 Neo4j 等外部图数据库，避免内存和连接开销 |
| **Schema 定向抽取** | 限定实体/关系类型，杜绝开放式 IE 的算力浪费 |
| **向量 + 图算法融合** | ChromaDB 负责语义召回，NetworkX 负责拓扑推理 |
| **异步批处理建图** | 建图与查询解耦，不阻塞在线服务 |
| **局部动态子图** | 仅对被召回的文档片段实时建图，而非离线构建全局图 |

### 整体架构

```
原始文档
   │
   ▼
[离线/异步] Schema 定向抽取 (LLM + 限定 Prompt)
   │
   ├──> ChromaDB: Chunk Collection（文档切片 + 向量）
   ├──> ChromaDB: Entity Collection（实体名 + 向量 + 元数据）
   ├──> ChromaDB: Relation Collection（关系描述 + 向量）
   └──> local graph.json（节点 + 边，供 NetworkX 加载）

[在线查询]
用户提问
   │
   ▼
① 向量寻点：Entity Collection → Top-K 种子实体
   │
   ▼
② 图谱发散：NetworkX 内存图 → 1~2 跳关联子图
   │
   ▼
③ 上下文组合：关系路径 + Chunk Collection 原文片段
   │
   ▼
④ LLM 生成最终回答
```

---

## 二、参考论文要点速查

| 论文 | 核心贡献 | 在本方案中的体现 |
|------|----------|-----------------|
| **LightRAG** (Guo et al., 2024) | 双层结构：低层实体 + 高层关系/主题，联合向量检索 | 三个 ChromaDB Collection 的分层设计 |
| **PathRAG** (Feb 2025) | 对图谱关系路径剪枝，去冗余边，降低遍历消耗 | 构建图时合并同义关系、限定边数上限 |
| **HippoRAG** (2024) | 模拟海马体：向量召回种子节点 → PPR 算法激活子图 | 向量寻点 + NetworkX 图发散的两阶段检索 |
| **Query-Driven GraphRAG** (2025) | 查询时在线局部建图，规避离线全局图构建 | 对召回 Chunk 进行实时小规模三元组抽取 |

---

## 三、工程实现：分阶段详解

### 阶段 1：Schema 定向抽取

#### 1.1 限定抽取 Schema

针对智能故障诊断类场景，在 Prompt 中硬性规定：

**实体类型（仅限以下 4 种）：**
- `COMPONENT`：系统组件（如"传感器A"、"驱动板"）
- `SYMPTOM`：故障现象（如"电流突变"、"过载报警"）
- `ERROR_CODE`：错误代码（如"E-04"）
- `SOLUTION`：解决方案（如"更换驱动板"）

**关系类型（仅限以下 4 种）：**
- `CAUSES`：引发
- `BELONGS_TO`：属于
- `RESOLVES`：解决
- `DIAGNOSES`：排查

#### 1.2 API 客户端封装（兼容 DeepSeek / OpenAI / 其他兼容接口）

DeepSeek 与 OpenAI 使用完全相同的接口协议，只需切换 `base_url` 和 `api_key`。

```python
# extract/llm_client.py
import os
import json
import time
import logging
from openai import OpenAI  # pip install openai>=1.0

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 支持的 API 预设（切换只需改 PROVIDER）
# ─────────────────────────────────────────────
API_CONFIGS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model":    "deepseek-chat",           # 或 deepseek-reasoner（R1）
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model":    "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
    },
    "moonshot": {                               # 月之暗面 Kimi
        "base_url": "https://api.moonshot.cn/v1",
        "model":    "moonshot-v1-8k",
        "api_key_env": "MOONSHOT_API_KEY",
    },
    "zhipu": {                                  # 智谱 GLM
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model":    "glm-4-flash",             # 免费额度模型
        "api_key_env": "ZHIPU_API_KEY",
    },
    "qwen": {                                   # 阿里云百炼 / 通义千问
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model":    "qwen-turbo",
        "api_key_env": "DASHSCOPE_API_KEY",
    },
}

PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")   # 通过环境变量切换


class LLMClient:
    """
    轻量级 LLM 客户端，统一封装外部 API 调用。
    自带重试、限速、JSON 清洗逻辑。
    """

    def __init__(self, provider: str = PROVIDER, temperature: float = 0.0):
        cfg = API_CONFIGS[provider]
        self.model = cfg["model"]
        self.temperature = temperature
        self.client = OpenAI(
            api_key=os.environ[cfg["api_key_env"]],
            base_url=cfg["base_url"],
        )
        logger.info(f"LLMClient initialized: provider={provider}, model={self.model}")

    def chat(
        self,
        user_prompt: str,
        system_prompt: str = "你是一个精确的信息抽取助手，只返回 JSON，不附加任何解释。",
        max_tokens: int = 2048,
        retries: int = 3,
        retry_delay: float = 2.0,
    ) -> str:
        """
        发起单次对话请求，返回模型回复的原始文本。
        失败时自动重试，超出次数则返回空字符串。
        """
        for attempt in range(1, retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt},
                    ],
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                logger.warning(f"API 调用失败 (attempt {attempt}/{retries}): {e}")
                if attempt < retries:
                    time.sleep(retry_delay * attempt)   # 指数退避
        return ""

    @staticmethod
    def parse_json(raw: str) -> list | dict | None:
        """
        清洗并解析 LLM 返回的 JSON 文本。
        兼容 ```json ... ``` 包裹 和 多余前后缀。
        """
        text = raw.strip()
        # 去除 markdown 代码块
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip().rstrip("```").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}\n原始内容: {raw[:200]}")
            return None
```

#### 1.3 抽取 Prompt 模板

```python
# extract/prompt_templates.py

EXTRACT_SYSTEM = "你是一个工业故障知识图谱抽取助手，只返回 JSON，不附加任何解释。"

EXTRACT_USER = """请从以下文本中，仅抽取符合 Schema 的三元组。

Schema 约束（严格遵守，不得自行扩展类型）：
- 实体类型：COMPONENT（组件）| SYMPTOM（故障现象）| ERROR_CODE（错误码）| SOLUTION（解决方案）
- 关系类型：CAUSES（引发）| BELONGS_TO（属于）| RESOLVES（解决）| DIAGNOSES（排查）

输出格式（仅返回 JSON 数组，无任何额外文字）：
[
  {{"head": "实体名", "head_type": "类型", "relation": "关系", "tail": "实体名", "tail_type": "类型"}},
  ...
]
若文本中无符合条件的三元组，返回空数组 []。

文本：
{chunk_text}
"""
```

#### 1.4 批量抽取脚本（含断点续传 + 限速控制）

```python
# extract/extractor.py
import json
import time
import logging
from pathlib import Path
from llm_client import LLMClient
from prompt_templates import EXTRACT_SYSTEM, EXTRACT_USER

logger = logging.getLogger(__name__)


def extract_triples_from_chunk(chunk_text: str, client: LLMClient) -> list[dict]:
    """对单个文本块调用外部 API 抽取三元组"""
    user_prompt = EXTRACT_USER.format(chunk_text=chunk_text)
    raw = client.chat(user_prompt, system_prompt=EXTRACT_SYSTEM)
    result = client.parse_json(raw)
    if isinstance(result, list):
        # 过滤掉字段不完整的三元组
        valid = [
            t for t in result
            if all(k in t for k in ("head", "head_type", "relation", "tail", "tail_type"))
        ]
        return valid
    return []


def batch_extract(
    chunks: list[str],
    client: LLMClient,
    output_path: str = "triples.json",
    request_interval: float = 0.3,   # 请求间隔（秒），防止触发速率限制
    resume: bool = True,             # 是否断点续传
) -> list[dict]:
    """
    批量抽取三元组并持久化到 JSON。
    支持断点续传：已处理的 chunk 索引记录在 output_path + '.progress'。
    """
    progress_path = Path(output_path).with_suffix(".progress.json")
    results: list[dict] = []
    start_idx = 0

    # 断点续传：读取上次进度
    if resume and progress_path.exists():
        with open(progress_path, "r", encoding="utf-8") as f:
            progress = json.load(f)
        start_idx = progress.get("last_index", 0)
        results = progress.get("results", [])
        logger.info(f"断点续传：从第 {start_idx} 个 chunk 继续")

    total = len(chunks)
    for i in range(start_idx, total):
        chunk = chunks[i]
        logger.info(f"[{i+1}/{total}] 抽取中 (长度={len(chunk)} 字)...")

        triples = extract_triples_from_chunk(chunk, client)
        results.extend(triples)
        logger.info(f"  → 抽取到 {len(triples)} 条三元组，累计 {len(results)} 条")

        # 每处理一个 chunk 立即保存进度（防止中断丢失）
        with open(progress_path, "w", encoding="utf-8") as f:
            json.dump({"last_index": i + 1, "results": results}, f, ensure_ascii=False)

        time.sleep(request_interval)

    # 保存最终结果
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 清理进度文件
    if progress_path.exists():
        progress_path.unlink()

    logger.info(f"完成！共抽取 {len(results)} 条三元组，已保存至 {output_path}")
    return results
```

#### 1.5 入口脚本与环境变量配置

```python
# extract/run_extract.py
"""
使用示例：
  export LLM_PROVIDER=deepseek
  export DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
  python run_extract.py --input chunks.json --output triples.json
"""
import argparse
import json
import logging
from llm_client import LLMClient
from extractor import batch_extract

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",    required=True,  help="切片 JSON 文件路径（list of str）")
    parser.add_argument("--output",   default="triples.json")
    parser.add_argument("--provider", default=None,   help="覆盖 LLM_PROVIDER 环境变量")
    parser.add_argument("--interval", type=float, default=0.3, help="请求间隔（秒）")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    client = LLMClient(provider=args.provider) if args.provider else LLMClient()
    batch_extract(chunks, client, output_path=args.output, request_interval=args.interval)

if __name__ == "__main__":
    main()
```

```bash
# .env（通过 python-dotenv 或手动 export 加载）
LLM_PROVIDER=deepseek          # 切换为 openai / moonshot / zhipu / qwen
DEEPSEEK_API_KEY=sk-xxxxxxxx
# OPENAI_API_KEY=sk-xxxxxxxx
# MOONSHOT_API_KEY=sk-xxxxxxxx
# ZHIPU_API_KEY=xxxxxxxx.xxxxxxxx
# DASHSCOPE_API_KEY=sk-xxxxxxxx
```

> **费用估算参考（以 DeepSeek-chat 为例）：**
> 每个 chunk 约 500 字，prompt + 输出合计约 800 tokens，
> DeepSeek-chat 价格约 ¥1/百万 tokens，
> **1000 个 chunk ≈ ¥0.8**，适合大批量离线建图。

---

### 阶段 2：混合存储架构

#### 2.1 ChromaDB 三层 Collection 设计

```python
# storage/chroma_store.py
import chromadb
from chromadb.utils import embedding_functions

# 推荐轻量级向量模型（显存 < 500MB）
EMBED_MODEL = "BAAI/bge-small-zh-v1.5"

class GraphRAGStore:
    def __init__(self, persist_dir: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBED_MODEL
        )
        # 三个 Collection
        self.chunks = self.client.get_or_create_collection(
            "chunks", embedding_function=self.embed_fn
        )
        self.entities = self.client.get_or_create_collection(
            "entities", embedding_function=self.embed_fn
        )
        self.relations = self.client.get_or_create_collection(
            "relations", embedding_function=self.embed_fn
        )

    def add_chunk(self, chunk_id: str, text: str, metadata: dict):
        self.chunks.add(
            ids=[chunk_id],
            documents=[text],
            metadatas=[metadata]
        )

    def add_entity(self, entity_id: str, name: str, entity_type: str):
        self.entities.add(
            ids=[entity_id],
            documents=[name],
            metadatas=[{"type": entity_type, "name": name}]
        )

    def add_relation(self, rel_id: str, head: str, relation: str, tail: str):
        text = f"{head} {relation} {tail}"
        self.relations.add(
            ids=[rel_id],
            documents=[text],
            metadatas=[{"head": head, "relation": relation, "tail": tail}]
        )

    def search_entities(self, query: str, top_k: int = 5) -> list[dict]:
        results = self.entities.query(query_texts=[query], n_results=top_k)
        return results["metadatas"][0]

    def search_chunks(self, query: str, top_k: int = 3) -> list[str]:
        results = self.chunks.query(query_texts=[query], n_results=top_k)
        return results["documents"][0]
```

#### 2.2 NetworkX 内存图管理

```python
# storage/graph_store.py
import json
import networkx as nx
from pathlib import Path

class KnowledgeGraph:
    def __init__(self, graph_path: str = "./graph.json"):
        self.graph_path = graph_path
        self.G = nx.DiGraph()
        self._load()

    def _load(self):
        """Flask 启动时从 JSON 加载图"""
        if Path(self.graph_path).exists():
            with open(self.graph_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for node in data.get("nodes", []):
                self.G.add_node(node["id"], **node.get("attrs", {}))
            for edge in data.get("edges", []):
                self.G.add_edge(edge["src"], edge["dst"], relation=edge["relation"])
            print(f"Graph loaded: {self.G.number_of_nodes()} nodes, {self.G.number_of_edges()} edges")

    def save(self):
        """持久化到 JSON"""
        data = {
            "nodes": [{"id": n, "attrs": dict(self.G.nodes[n])} for n in self.G.nodes],
            "edges": [{"src": u, "dst": v, "relation": self.G[u][v]["relation"]}
                      for u, v in self.G.edges]
        }
        with open(self.graph_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_triple(self, head: str, relation: str, tail: str,
                   head_type: str = "", tail_type: str = ""):
        self.G.add_node(head, entity_type=head_type)
        self.G.add_node(tail, entity_type=tail_type)
        self.G.add_edge(head, tail, relation=relation)

    def expand_subgraph(self, seed_entities: list[str], hops: int = 2) -> list[dict]:
        """从种子节点扩展 N 跳子图，返回关系路径列表"""
        paths = []
        visited = set(seed_entities)

        for seed in seed_entities:
            if seed not in self.G:
                continue
            # BFS 扩展
            frontier = {seed}
            for _ in range(hops):
                next_frontier = set()
                for node in frontier:
                    for neighbor in list(self.G.successors(node)) + list(self.G.predecessors(node)):
                        if neighbor not in visited:
                            edge_data = self.G.get_edge_data(node, neighbor) or \
                                        self.G.get_edge_data(neighbor, node)
                            relation = edge_data.get("relation", "关联") if edge_data else "关联"
                            paths.append({
                                "from": node,
                                "relation": relation,
                                "to": neighbor
                            })
                            visited.add(neighbor)
                            next_frontier.add(neighbor)
                frontier = next_frontier
        return paths

    def build_from_triples(self, triples: list[dict]):
        """从抽取结果批量建图"""
        for t in triples:
            self.add_triple(
                head=t["head"], relation=t["relation"], tail=t["tail"],
                head_type=t.get("head_type", ""), tail_type=t.get("tail_type", "")
            )
        self.save()
```

---

### 阶段 3：检索增强推理链路

#### 3.1 四步 RAG Pipeline

```python
# rag/pipeline.py

class GraphRAGPipeline:
    def __init__(self, store: GraphRAGStore, graph: KnowledgeGraph, llm_client):
        self.store = store
        self.graph = graph
        self.llm = llm_client

    def retrieve_and_reason(self, query: str) -> str:
        # ① 向量寻点：找 Top-K 种子实体
        seed_entities_meta = self.store.search_entities(query, top_k=5)
        seed_names = [m["name"] for m in seed_entities_meta]

        # ② 图谱发散：1~2 跳关联子图
        subgraph_paths = self.graph.expand_subgraph(seed_names, hops=2)

        # ③ 组合上下文
        raw_chunks = self.store.search_chunks(query, top_k=3)
        context = self._build_context(seed_names, subgraph_paths, raw_chunks)

        # ④ LLM 生成回答
        return self._generate(query, context)

    def _build_context(self, seeds, paths, chunks) -> str:
        path_lines = "\n".join(
            f"  - {p['from']} --[{p['relation']}]--> {p['to']}" for p in paths[:20]
        )
        chunk_text = "\n\n".join(chunks)
        return f"""【关联实体】
{', '.join(seeds)}

【知识图谱路径】
{path_lines}

【相关原文片段】
{chunk_text}"""

    def _generate(self, query: str, context: str) -> str:
        prompt = f"""你是一个智能故障诊断助手，请根据以下背景知识回答问题。

背景知识：
{context}

用户问题：{query}

请给出逻辑清晰、有理有据的诊断建议："""
        return self.llm.generate(prompt)
```

#### 3.2 Flask 路由集成

```python
# app.py
from flask import Flask, request, jsonify
from storage.chroma_store import GraphRAGStore
from storage.graph_store import KnowledgeGraph
from rag.pipeline import GraphRAGPipeline

app = Flask(__name__)

# 服务启动时加载图（NetworkX 内存图，毫秒级）
store = GraphRAGStore()
graph = KnowledgeGraph()
pipeline = GraphRAGPipeline(store, graph, llm_client=YOUR_LLM_CLIENT)

@app.route("/query", methods=["POST"])
def query():
    data = request.json
    question = data.get("question", "")
    if not question:
        return jsonify({"error": "question is required"}), 400
    answer = pipeline.retrieve_and_reason(question)
    return jsonify({"answer": answer})
```

---

### 阶段 4：工程与硬件妥协策略

#### 4.1 异步建图（避免阻塞查询接口）

```python
# tasks/ingest.py
import threading
from queue import Queue

ingest_queue = Queue()

def ingest_worker():
    """后台线程：持续处理建图任务"""
    while True:
        task = ingest_queue.get()
        if task is None:
            break
        chunks = task["chunks"]
        triples = batch_extract(chunks, llm_client)
        graph.build_from_triples(triples)
        # 同步更新 ChromaDB
        for t in triples:
            store.add_entity(t["head"], t["head"], t["head_type"])
            store.add_entity(t["tail"], t["tail"], t["tail_type"])
            store.add_relation(
                f"{t['head']}-{t['relation']}-{t['tail']}",
                t["head"], t["relation"], t["tail"]
            )
        ingest_queue.task_done()

# Flask 启动时开启后台线程
worker = threading.Thread(target=ingest_worker, daemon=True)
worker.start()

@app.route("/ingest", methods=["POST"])
def ingest():
    """文档摄入接口：立即返回，异步处理"""
    data = request.json
    ingest_queue.put({"chunks": data["chunks"]})
    return jsonify({"status": "queued"})
```

#### 4.2 模型选型建议

| 用途 | 推荐模型 | 显存占用 |
|------|----------|----------|
| 文本向量化 | `BAAI/bge-small-zh-v1.5` | ~130MB |
| 三元组抽取 LLM | Qwen2.5-7B-Instruct Q4_K_M | ~4GB |
| 在线问答 LLM | 同上，或调用 API | — |

> **建议**：三元组抽取放在夜间/闲时批处理，不占用在线查询资源。

#### 4.3 图规模控制策略

```python
# 构建图时的剪枝策略（参考 PathRAG）
MAX_EDGES_PER_NODE = 20  # 单节点最大出边数
MIN_TRIPLE_FREQUENCY = 2  # 出现少于 N 次的三元组丢弃

def prune_graph(G: nx.DiGraph) -> nx.DiGraph:
    """剪枝：限制节点出边数，去除低频边"""
    for node in list(G.nodes):
        out_edges = list(G.out_edges(node, data=True))
        if len(out_edges) > MAX_EDGES_PER_NODE:
            # 保留权重最高的 N 条边
            sorted_edges = sorted(out_edges, key=lambda e: e[2].get("weight", 1), reverse=True)
            for _, v, _ in sorted_edges[MAX_EDGES_PER_NODE:]:
                G.remove_edge(node, v)
    return G
```

---

## 四、目录结构参考

```
project/
├── app.py                    # Flask 主入口
├── config.py                 # 配置（模型路径、ChromaDB路径等）
│
├── storage/
│   ├── chroma_store.py       # ChromaDB 三层 Collection 管理
│   └── graph_store.py        # NetworkX 内存图管理
│
├── rag/
│   ├── pipeline.py           # 四步 RAG 推理链路
│   └── prompt_templates.py   # Prompt 模板
│
├── extract/
│   ├── llm_client.py         # 外部 API 客户端（DeepSeek/OpenAI 兼容接口）
│   ├── prompt_templates.py   # 抽取 Prompt 模板
│   ├── extractor.py          # 单块抽取 + 批量抽取（断点续传）
│   └── run_extract.py        # CLI 入口脚本
│
├── tasks/
│   └── ingest.py             # 异步文档摄入任务队列
│
├── data/
│   ├── graph.json            # 持久化图数据（节点+边）
│   └── chroma_db/            # ChromaDB 持久化目录
│
└── requirements.txt
```

---

## 五、依赖安装

```bash
pip install flask chromadb networkx sentence-transformers openai python-dotenv
```

```
# requirements.txt
flask>=3.0
chromadb>=0.5
networkx>=3.3
sentence-transformers>=3.0
openai>=1.0          # DeepSeek / OpenAI 兼容接口统一使用此库
python-dotenv>=1.0   # 从 .env 文件加载 API Key
```

---

## 六、快速启动 Checklist

- [ ] 配置向量模型路径（`BAAI/bge-small-zh-v1.5`）
- [ ] 初始化 ChromaDB 三个 Collection
- [ ] 准备原始文档 → 切块 → 异步抽取三元组
- [ ] 执行 `build_from_triples()` 构建初始图，保存 `graph.json`
- [ ] 启动 Flask 服务（图在启动时自动加载到内存）
- [ ] 调用 `/query` 接口测试端到端问答效果
- [ ] 根据业务调整 Schema 中的实体/关系类型

---

## 七、性能预期与扩展方向

| 指标 | 预期值 |
|------|--------|
| NetworkX 图加载时间（10万节点） | < 2 秒 |
| 单次查询延迟（不含 LLM） | < 200ms |
| ChromaDB 向量检索（10万条） | < 100ms |
| 三元组抽取速度（7B量化模型） | ~5–10 条/秒 |

**后续可扩展方向：**
- 接入 PPR（个性化 PageRank）替代 BFS 扩展，进一步提升路径质量（HippoRAG 核心）
- 支持多模态输入（图片+文本联合建图，Query-Driven GraphRAG 方向）
- 增加图谱版本管理，支持增量更新而非全量重建
