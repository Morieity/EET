# 上下文管理代码阅读教程

## 1. 这份教程解决什么问题

目标不是“审查代码质量”，而是让你快速看懂这套功能的代码怎么串起来、每一层做什么、出问题时该先看哪。

读完后你应该能回答 4 个问题：
- 请求从哪里进入上下文管理逻辑。
- 编排顺序在哪里定义。
- 每个算法模块在链路里负责什么。
- 日志为什么可以在 DI 层统一开关。

## 2. 先建立全局图

先记住这条主链路：

1. 应用启动注册依赖（DI）
2. ChatUseCase 收到问题并检索数据
3. ContextManager 按固定顺序编排
4. 结果回到 ChatUseCase 组装消息并流式输出

对应文件：
- `Backend/Web/app_factory.py`
- `Backend/Application/UseCases/ChatUseCase.py`
- `Backend/Application/ContextManagement/ContextManager.py`

## 3. 第一步：从入口开始读（不要先看算法）

### 3.1 看 DI 装配

文件：`Backend/Web/app_factory.py`

先看两件事：
- `DefaultContextManager` 是在哪里实例化并注入到 `ChatUseCase` 的。
- `CONTEXT_MODULE_LOG_ENABLED` 如何决定注入 `PythonLoggerAdapter` 还是 `NullLogger`。

你会得到结论：上下文功能和日志开关都在 DI 层集中控制。

### 3.2 看调用点

文件：`Backend/Application/UseCases/ChatUseCase.py`

重点看 `execute()` 内 3 段：
- 检索 `seed_names / graph_paths / sources`。
- 调用 `self._context_manager.prepare_context(...)`。
- 回退逻辑：失败时走 `_build_enhanced_context(...)`。

读完这一步，你已经知道“功能怎么被触发”和“为什么不会因为上下文模块失败而中断主流程”。

## 4. 第二步：读契约，再读实现

### 4.1 先看接口和数据结构

按顺序读：
- `Backend/Application/Interfaces/IContextManager.py`
- `Backend/Application/ContextManagement/ContextManagerTypes.py`
- `Backend/Application/ContextManagement/ContextTypes.py`

重点不是细节，而是回答：
- 输入有哪些。
- 输出 `ContextPreparationResult` 包含哪些字段。
- 哪些字段会被 ChatUseCase 实际消费。

### 4.2 再看编排实现

文件：`Backend/Application/ContextManagement/ContextManager.py`

只盯 `prepare_context()`，按函数内注释顺序读，不要跳读：

1. `PathPruningAlgorithm`
2. `MMRDeduplicationAlgorithm`
3. `RetrievalReorderingAlgorithm`
4. `TokenBudgetingAlgorithm`
5. 条件压缩（history/vector/kg）
6. 最终 `context` 与 `user_content` 组装

阅读技巧：每读完一步，立即在纸上记“输入 -> 输出变化”。

## 5. 第三步：逐个算法模块看“职责边界”

目录：`Backend/Application/ContextManagement/Algorithms/`

建议顺序：
- `PathPruningAlgorithm.py`
- `MMRDeduplicationAlgorithm.py`
- `RetrievalReorderingAlgorithm.py`
- `TokenBudgetingAlgorithm.py`
- `HistoryTieringAlgorithm.py`
- `QueryAwareCompressionAlgorithm.py`
- `QueryPlacementAlgorithm.py`

每个文件只回答 3 个问题：
- 它删除了什么。
- 它重排了什么。
- 它是否改变了语义内容。

如果一个模块既做“过滤”又做“重写”，要特别标记，这通常是后续 bug 高发点。

## 6. 第四步：单独理解日志逻辑

先看接口，再看实现，再回到注入点：
- `Backend/Application/Interfaces/ILogger.py`
- `Backend/Infrastructure/logging/ContextModuleLogger.py`
- `Backend/Web/app_factory.py`

最后回到 `ContextManager.py` 看 `_log_debug(...)` 调用点。

你要确认两点：
- 业务代码不直接依赖 Python logging。
- 关闭开关后，日志路径变成 `NullLogger`，代码行为保持一致。

## 7. 第五步：用测试反证你的理解

测试文件：`tests/test_context_manager_unit.py`

建议这样读：
- 先读测试数据构造（它在模拟什么场景）。
- 再读断言（它认为“正确结果”是什么）。
- 最后回到实现对照断言来源。

运行命令：

```bash
c:/Users/tangx/Desktop/RAG/.venv/Scripts/python.exe -m pytest tests/test_context_manager_unit.py -q
```

## 8. 一条可执行的 30 分钟阅读路径

1. 5 分钟：`app_factory.py` + `ChatUseCase.py`
2. 8 分钟：`IContextManager.py` + `ContextManagerTypes.py` + `ContextTypes.py`
3. 10 分钟：`ContextManager.py`（只看 `prepare_context`）
4. 5 分钟：算法目录按顺序扫一遍
5. 2 分钟：看 `test_context_manager_unit.py` 的断言

## 9. 阅读完成的判断标准

如果你能独立回答以下问题，说明已经读懂：
- 为什么 `sources` 事件返回的是编排后的 sources。
- 哪个阈值会触发 history tiering，哪个会触发 vector 压缩。
- Query 在哪里被保证放到最后。
- 日志开关为什么应该放在 DI，而不是业务函数里。

如果还不能回答，回到第 4 节只重读 `prepare_context()` 即可，不要重复全量阅读。
