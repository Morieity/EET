# 上下文管理代码文档（Step 4）

## 1. 文档目的

本文档描述当前已落地的上下文管理代码结构、职责边界与关键约束，用于开发、维护与审阅。

## 2. 实施决议

- 已执行：Step 1（论文到算法模块）、Step 2（主链路接入）。
- 决议：跳过原 Step 3。理由是原 Step 3 将一个已实现能力按阶段拆分为重复性子任务，不符合工程最小增量与单一事实源原则。
- 当前执行：直接进入 Step 4，输出规范化文档与审阅基线。

## 3. 架构与职责边界

- 应用层编排：`Backend/Application/ContextManagement/ContextManager.py`
  - `DefaultContextManager` 负责上下文准备与算法编排。
  - 不直接依赖基础设施实现，只依赖应用层接口与算法模块。
- 应用层契约：
  - `Backend/Application/Interfaces/IContextManager.py`
  - `Backend/Application/Interfaces/ILogger.py`
- 数据契约：
  - `Backend/Application/ContextManagement/ContextTypes.py`
  - `Backend/Application/ContextManagement/ContextManagerTypes.py`
- 算法注册与实现：
  - `Backend/Application/ContextManagement/AlgorithmRegistry.py`
  - `Backend/Application/ContextManagement/Algorithms/*.py`
- DI 装配：`Backend/Web/app_factory.py`
- 调用入口：`Backend/Application/UseCases/ChatUseCase.py`

## 4. 关键类型

### 4.1 ContextManagerConfig

文件：`Backend/Application/ContextManagement/ContextManagerTypes.py`

核心字段：
- `max_context_tokens`: 上下文窗口上限。
- `max_history_rounds`: 参与历史装配的最大轮次。
- `mmr_top_k`, `mmr_relevance_weight`: MMR 去重参数。
- `min_path_confidence`, `max_graph_paths`: 图路径裁剪参数。
- `history_hot_size`, `history_warm_size`: 历史分层参数。
- `compression_keep_rate`, `compression_min_chars`: 向量压缩参数。

### 4.2 ContextPreparationResult

文件：`Backend/Application/ContextManagement/ContextManagerTypes.py`

核心字段：
- `context`: 最终拼接的上下文字符串。
- `user_content`: 追加到最后一条 user 消息的内容（保证 Query 在末尾）。
- `history_messages`: 历史消息块。
- `sources`, `graph_paths`, `seed_names`: 处理后的证据集合。
- `budget_actions`: 预算触发动作列表。
- `prompt_token_estimate`, `budget_plan`: 可观测性信息。

## 5. 模块职责清单

- `MMRDeduplicationAlgorithm`: 去重并平衡相关性/新颖性。
- `RetrievalReorderingAlgorithm`: 边界感知重排序。
- `TokenBudgetingAlgorithm`: 预算计算与阈值触发动作判定。
- `HistoryTieringAlgorithm`: 对话历史分层汇总。
- `PathPruningAlgorithm`: 图路径过滤与多样性保留。
- `QueryAwareCompressionAlgorithm`: 查询感知压缩（规则型实现）。
- `QueryPlacementAlgorithm`: 用户查询尾位保障。

## 6. Chat 主链路接入方式

文件：`Backend/Application/UseCases/ChatUseCase.py`

- 优先调用 `IContextManager.prepare_context()`。
- 若上下文管理异常，自动回退到旧逻辑 `_build_enhanced_context()`。
- 对外 SSE 协议不变（`conversation/sources/token/done/error`）。

## 7. 工程约束

- 单一编排入口：上下文处理只能由 `DefaultContextManager` 聚合。
- 依赖方向：应用层不反向依赖基础设施具体类。
- 可替换性：`IContextManager` 与 `ILogger` 必须可替换。
- 回退安全：ContextManager 异常不可中断主对话流程。

## 8. 后续演进建议（不改变当前决议）

- 将预算阈值与压缩参数迁移到集中配置文件。
- 为 `ContextPreparationResult` 增加版本字段，便于跨版本审计。
- 增加端到端回归测试，覆盖超预算与图路径缺失场景。
