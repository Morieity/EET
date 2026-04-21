# 上下文管理编排文档（Step 4）

## 1. 范围与目标

本文档定义上下文编排的固定顺序、输入输出契约、触发条件与回退策略，作为实现与审阅的统一依据。

## 2. 固定编排顺序（不可重排）

编排实现：`Backend/Application/ContextManagement/ContextManager.py`

1. Path pruning：图路径剪枝
2. MMR deduplication：向量结果去冗余
3. Retrieval reordering：检索结果重排序
4. Token-budget evaluation：预算评估与动作判定
5. Conditional compression：历史分层与向量压缩
6. Final assembly：最终上下文与 Query 尾位组装

该顺序由 `prepare_context()` 内部直接编码，必须保持确定性。

## 3. 阶段输入输出

### 阶段 1：Path pruning

- 输入：`graph_paths`
- 输出：`pruned_paths`
- 约束：仅保留满足 `min_path_confidence` 的关系，并限制 `max_graph_paths`。

### 阶段 2：MMR deduplication

- 输入：`sources`
- 输出：`mmr_sources`
- 约束：先精确去重，再按 MMR 选取。

### 阶段 3：Retrieval reordering

- 输入：`mmr_sources`
- 输出：`reordered_sources`
- 约束：边界优先排序，不删除条目。

### 阶段 4：Token-budget evaluation

- 输入：`history_messages + user_content` 的 token 估计
- 输出：`budget_plan`, `budget_actions`
- 动作阈值：
  - `>0.6`：`compress_history_tier2`
  - `>0.8`：`compress_history_tier3`, `compress_vector_docs_keep_50pct`
  - `>0.9`：`kg_one_hop_only`, `remove_kg_community_summary`, `vector_top_k_hard_cap`

### 阶段 5：Conditional compression

- 历史压缩：触发 `compress_history_tier2` 时执行分层摘要。
- 向量压缩：触发 `compress_vector_docs_keep_50pct` 时执行查询感知压缩。
- 强制截断：触发 `vector_top_k_hard_cap` 时强制上限为 3。
- 图路径降级：触发 `kg_one_hop_only` 时限制为种子实体相关路径。

### 阶段 6：Final assembly

- 重新构建 `context`。
- 通过 `QueryPlacementAlgorithm` 保障 query 位于用户消息末尾。
- 产出 `ContextPreparationResult`。

## 4. 回退策略

接入点：`Backend/Application/UseCases/ChatUseCase.py`

- 正常：使用 `ContextPreparationResult` 中的 `history_messages` 与 `user_content`。
- 异常：捕获异常后回退到 `_build_enhanced_context()`，保持服务可用。

## 5. 不变量（必须成立）

- Query 始终在最后一条 user 消息中。
- ContextManager 的异常不应中断 SSE 输出。
- `sources` 事件输出应与实际参与回答的数据一致。
- 编排动作只依赖输入数据与配置，不依赖外部可变全局状态。

## 6. 反模式（禁止）

- 在 `ChatUseCase` 内重复实现编排细节。
- 在编排阶段直接调用基础设施外部服务。
- 按功能重复拆分同一能力形成多套并行流程。

## 7. 变更准入规则

- 变更顺序：需给出性能或正确性证据，并更新本文件。
- 变更阈值：需补充测试数据和回归脚本。
- 新增动作：需提供回退路径与日志事件。
