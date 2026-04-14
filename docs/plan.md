## Plan: 上下文管理论文到工程落地

基于 docs 中的论文索引与现有后端主链路，采用“先证据化算法映射，再最小侵入接入，再分阶段增强”的路线。推荐 4 步实施（满足你要求的 3-4 步）：第 1 步提炼论文核心算法并形成可执行算法卡；第 2 步在 ChatUseCase 前后建立 Context Manager 编排位点；第 3 步按阈值和风险分四个里程碑增量上线；第 4 步输出独立算法流程文档并建立验收基线。

**Steps**
1. 第一步：论文检索与核心算法提取（证据层，先行步骤）
- 从 docs/rag_context_prompt_architecture.md 的论文池筛选与上下文管理强相关算法，形成“算法卡片表”：算法名、来源论文、输入、输出、触发条件、放置流程位置、收益、代价、失败模式。
- 先做 MVP 算法分组：Retrieval Reordering、MMR 去冗余、Token Budgeting、History Tiering、Query-at-End。
- 再做增强算法分组：LongLLMLingua/LLMLingua-2 压缩、PathRAG 路径剪枝、HyDE/Query Decomposition。
- 暂缓算法分组：ICAE/需要训练或高侵入改造的方法。
- 交付物：论文-算法映射清单、MVP/增强优先级、参数建议（默认阈值与降级策略）。
- 依赖关系：无；并行性：可与第二步中的“目录与文件骨架设计”并行。

2. 第二步：上下文管理流程设计与项目接入点对齐（架构层，依赖第一步）
- 以现有链路为主轴重排流程：检索完成 → 去冗余/MMR → Reordering（首尾高相关）→ Token 预算评估 → 压缩触发 → 五层 Prompt 组装（Query 固定末尾）。
- 在应用层增加 Context Manager 契约与结果对象，避免把上下文策略塞进 LLMService。
- ChatUseCase 改造原则：保留现有 GraphRAG 检索调用点，不改检索器职责；只替换上下文融合与历史装配逻辑。
- 数据层策略：先不强依赖迁移即可上线，若需可观测性再给 chat_rounds 增加上下文 token/质量字段。
- 依赖关系：依赖第一步算法卡；并行性：接口定义与数据模型可并行，UseCase 接入阻塞后续实现。

3. 第三步：上下文管理功能按 4 个里程碑落地（实施层，满足“拆分三到四步”）
- M1（最低风险，先上线）：向量检索阈值收紧 + MMR 去冗余 + Retrieval Reordering。
- M2（预算控制）：Token Budget 分配与动态触发（0.6/0.8/0.9）接入，保证 System 与 Query 不压缩。
- M3（历史管理）：History Tiering（三层）上线，先用启发式摘要替代训练型压缩器。
- M4（增强压缩与图剪枝）：接入 Query-aware 压缩与 Path 剪枝，配合回退策略。
- 里程碑依赖：M1 先于 M2；M2 先于 M3；M4 依赖 M2/M3 的预算与元数据。
- 并行性：M1 中阈值治理与排序可并行；M3 的历史摘要与持久化元数据可并行。

4. 第四步：单独文档产出与验证闭环（文档与验收层，依赖第二步和第三步）
- 在 docs 目录新增一份“上下文管理核心算法与流程”独立文档（由你提到的图示流程单独展开，不与总览文档混写）。
- 文档结构固定为：算法总览表、执行流程图、触发阈值与降级矩阵、项目模块映射、3-4 步实施路线、验收清单。
- 同步给出两种路线：4 步标准版（推荐）与 3 步合并版（把 M3+M4 合并）。
- 验收前必须完成：长对话、超预算、检索噪声、图谱缺失四类场景验证。

**Relevant files**
- c:/Users/tangx/Desktop/RAG/docs/rag_context_prompt_architecture.md — 论文池与五层 Prompt 设计基线。
- c:/Users/tangx/Desktop/RAG/Backend/Application/UseCases/ChatUseCase.py — 当前上下文融合、历史拼装与消息顺序主入口。
- c:/Users/tangx/Desktop/RAG/Backend/Web/app_factory.py — Context Manager 的依赖注入入口。
- c:/Users/tangx/Desktop/RAG/Backend/Infrastructure/vectorstore/ChromaVectorStoreRepository.py — 向量检索阈值、score 字段与 Top-K 行为。
- c:/Users/tangx/Desktop/RAG/Backend/Infrastructure/graphstore/NetworkXGraphRepository.py — 子图扩展与路径剪枝落点。
- c:/Users/tangx/Desktop/RAG/Backend/Domain/Entities/conversation.py — 历史轮次对象扩展位。
- c:/Users/tangx/Desktop/RAG/Backend/Infrastructure/persistence/ConversationRepository.py — 历史读写与元数据持久化落点。
- c:/Users/tangx/Desktop/RAG/Backend/Infrastructure/persistence/database.py — 上下文字段迁移与兼容策略。
- c:/Users/tangx/Desktop/RAG/tests/test_chat_api.py — 现有回归基线与 SSE 行为验证。

**Verification**
1. 论文到算法映射验收：每个算法卡都要有来源论文、触发条件和可执行参数，且能映射到项目具体模块。
2. 流程正确性验收：在 Chat 主链路中验证顺序为“检索→去冗余/排序→预算→压缩→拼装”，并确认 Query 在末尾。
3. 预算触发验收：构造短/中/长三档输入，验证 0.6/0.8/0.9 阈值触发与降级动作一致。
4. 历史连贯性验收：10+ 轮对话后关键事实保留率与回答稳定性不低于基线。
5. 回归验收：保持现有 SSE 事件完整（conversation/sources/token/done/error）与已有接口不破坏。
6. 文档一致性验收：独立文档中的算法、阈值、流程与代码设计文档一致，不出现“双版本规则”。

**Decisions**
- 包含范围：论文算法提取、流程接入设计、3-4 步实施拆解、独立文档规划与验收方案。
- 不包含范围：本轮不做代码实现、不引入训练型记忆模型、不做多 Agent 运行时改造。
- 推荐执行版本：4 步标准版优先，3 步版作为人力紧张时的合并降配方案。
- 命名约定建议：新增文档聚焦“核心算法+流程”，避免与现有总览文档重复。

**Further Considerations**
1. 里程碑选择建议：Option A（4 步标准版）质量更稳；Option B（3 步合并版）交付更快但调试复杂度更高。
2. 压缩策略建议：先规则型（可解释）后学习型（高收益），避免早期观测盲区。
3. 指标建议：至少跟踪 token 利用率、去重率、回答一致性、回退触发率四项。