# Research: 智能故障诊断与故障树生成系统

**Date**: 2026-03-24  
**Feature**: 001-fault-diagnosis-tree  
**Purpose**: Resolve all NEEDS CLARIFICATION items and evaluate technology choices

---

## R-001: PostgreSQL 集成模式

**Decision**: 使用 SQLAlchemy ORM + Data Mapper 模式

**Rationale**:
- SQLAlchemy ORM 提供成熟的迁移工具（Alembic），模式演进可控
- Data Mapper 模式将 ORM 模型与 Domain 实体分离：Infrastructure 层定义 SQLAlchemy Table 映射，Domain 层纯 Python dataclass 不依赖任何 ORM
- 符合宪法 DIP 原则：Application 层通过 Protocol 接口访问存储，Infrastructure 层实现具体的 SQLAlchemy 仓储
- 与现有 Protocol 模式（`VectorStoreRepository`, `RetrieverFactory`）一致

**Alternatives Considered**:
- Raw psycopg2：无迁移支持，手写 SQL 维护成本高 → 拒绝
- SQLAlchemy Core（无 ORM）：比 ORM 更底层，对简单 CRUD 场景过度复杂 → 拒绝
- SQLite：轻量但不适合并发写入和生产扩展 → 拒绝

**Integration Pattern**:
- `app_factory.py` 中创建 SQLAlchemy engine/session
- Infrastructure 层的 Repository 类接收 session factory 作为构造参数
- Domain 实体为纯 Python dataclass，由 Infrastructure 层负责 Domain ↔ ORM 转换

---

## R-002: 双存储协调（ChromaDB + PostgreSQL）

**Decision**: PostgreSQL 为事实源（ACID），ChromaDB 为检索优化的异步副本

**Rationale**:
- 用户要求明确：PostgreSQL 负责对话会话和案例的结构化持久存储，ChromaDB 专门服务于 LLM 对话检索
- ChromaDB 不支持 ACID 事务，无法与 PostgreSQL 做两阶段提交
- 对于知识库文档：直接写入 ChromaDB（已有流程），元数据可选同步到 PostgreSQL
- 对于案例入库：先写 PostgreSQL（事务安全），成功后再将案例文本写入 ChromaDB 供检索
- 失败恢复：案例原始数据在 PostgreSQL 中安全，ChromaDB 写入失败可重试

**Alternatives Considered**:
- 仅 ChromaDB：丢失结构化查询能力（如按时间、状态筛选案例） → 拒绝
- 两阶段提交：ChromaDB 不支持事务回滚 → 不可行
- 事件溯源 + Outbox：当前阶段过度设计 → 拒绝，后续可升级

**Storage Responsibility Division**:

| 数据类型 | PostgreSQL | ChromaDB |
|----------|:----------:|:--------:|
| 文档知识库 | — | ✅ 向量检索 |
| 诊断会话（Session） | ✅ 结构化存储 | — |
| 对话消息（Message） | ✅ 结构化存储 | — |
| 故障树（FaultTree） | ✅ JSON 存储 | — |
| 案例（Case） | ✅ 结构化存储 | ✅ 案例文本向量化（供相似案例检索） |

---

## R-003: DDD 聚合根设计

**Decision**: 两个独立聚合根 — `DiagnosisSession` 和 `FaultTree`

**Rationale**:
- 用户明确要求分别设计聚合根
- 两者生命周期不同：会话可能持续数十轮对话，故障树在会话结束后独立存在
- 聚合根负责内部一致性：DiagnosisSession 管理消息列表和诊断状态，FaultTree 管理节点树结构和案例生命周期
- 聚合间通过 ID 引用关联（FaultTree 持有 session_id），不直接持有对方实例

**聚合 1 — DiagnosisSession**:
- 根实体：`DiagnosisSession`（会话 ID、创建时间、状态、对话历史）
- 内部实体：`ChatMessage`（角色、内容、时间戳）
- 值对象：`SessionStatus`（进行中/已完成/已生成故障树）
- 不变量：消息列表有序、状态转换合法（不能从已完成回到进行中）

**聚合 2 — FaultTree**:
- 根实体：`FaultTree`（故障树 ID、关联会话 ID、根节点、创建时间）
- 内部实体：`FaultTreeNode`（节点 ID、名称、类型、门类型、子节点列表、描述）
- 值对象：`NodeType`（事件/门/基本原因）、`GateType`（AND/OR/XOR）
- 不变量：树结构合法（根节点唯一、无环）、JSON 可序列化

**Case 作为 FaultTree 聚合的一部分**:
- `Case` 是 FaultTree 确认后的快照状态，包含确认时间、标准化状态
- 通过 FaultTree 的状态转换（draft → confirmed → standardized）管理

**Alternatives Considered**:
- 单一聚合包含 Session + FaultTree：违反 SRP，生命周期耦合 → 拒绝
- Case 作为独立聚合根：Case 与 FaultTree 强关联（1:1），拆分增加复杂度 → 拒绝

---

## R-004: 文档去重策略

**Decision**: 三级去重 — 内容哈希 → 元数据比对 → 嵌入相似度

**Rationale**:
- Level 1（内容哈希）：对每个切分后的文档片段计算 SHA-256 哈希，与已存储哈希比对，精确去除完全重复
- Level 2（元数据比对）：同一来源文件 + 相同页码范围的片段视为重复
- Level 3（嵌入相似度）：对通过 Level 1/2 的片段，计算与已有向量的余弦相似度，阈值 > 0.95 视为近似重复
- 哈希表存储在内存中（上传时加载），不依赖额外数据库查询

**Alternatives Considered**:
- 仅哈希去重：无法识别措辞微调的近似重复 → 不够
- 仅嵌入相似度：计算成本高，且对完全相同内容浪费资源 → 效率低
- TF-IDF / MinHash：引入额外依赖，对短文本片段效果一般 → 过度设计

---

## R-005: 多轮对话管理

**Decision**: Application 层手动管理对话历史，不使用 LangChain 内置 Memory

**Rationale**:
- LangChain 的 `ConversationBufferMemory` 是内存态，服务重启后丢失
- 对话历史需要持久化到 PostgreSQL（用户要求），LangChain Memory 不支持
- 手动管理可精确控制上下文窗口：保留最近 N 轮 + 摘要，适配 LLM Token 限制
- 符合宪法 DIP 原则：对话存储通过 Protocol 接口注入，不锁定 LangChain 实现
- 更易测试：Use Case 接收消息列表，不依赖 LangChain 全局状态

**Implementation Pattern**:
1. `DiagnoseDiagnosisUseCase.execute()` 接收 session_id + 新消息
2. 从仓储加载 `DiagnosisSession` 聚合根（含历史消息）
3. 截取最近 N 条消息（Token 预算管理）
4. 拼接 system prompt + RAG 检索上下文 + 对话历史 + 用户消息
5. 调用 LLM 获取回复
6. 将用户消息和 AI 回复追加到聚合根并持久化

**Alternatives Considered**:
- LangChain ConversationBufferMemory：无持久化、不可测试 → 拒绝
- LangChain ConversationSummaryMemory：增加 LLM 调用成本 → 当前阶段拒绝
- Redis 缓存对话：引入额外组件，PostgreSQL 已满足需求 → 过度设计

---

## R-006: 故障树 JSON Schema

**Decision**: 参考 IEC 61025 的自定义简化 Schema

**Rationale**:
- IEC 61025 完整标准过于复杂（含可靠性计算、概率分析），当前阶段仅需结构化表示
- 保留核心概念：事件节点、逻辑门、基本原因，支持后续扩展

**JSON Structure**:

```json
{
  "id": "ft-uuid",
  "name": "故障树名称",
  "description": "故障描述摘要",
  "session_id": "关联会话 ID",
  "created_at": "ISO8601",
  "root": {
    "id": "node-uuid",
    "name": "顶事件名称",
    "type": "intermediate_event",
    "gate_type": "OR",
    "description": "顶层故障描述",
    "children": [
      {
        "id": "node-uuid",
        "name": "中间事件",
        "type": "intermediate_event",
        "gate_type": "AND",
        "description": "...",
        "children": [
          {
            "id": "node-uuid",
            "name": "基本原因",
            "type": "basic_event",
            "gate_type": null,
            "description": "最底层原因",
            "children": []
          }
        ]
      }
    ]
  }
}
```

**Node Types**: `basic_event` | `intermediate_event` | `undeveloped_event` | `external_event` | `conditional_event`

**Gate Types**: `AND` | `OR` | `XOR` | `INHIBIT` | `PRIORITY_AND` (null for leaf nodes)

**Alternatives Considered**:
- 完整 IEC 61025 Schema（含 MTBF、失效率）：当前阶段不需要 → 后续扩展
- 扁平列表 + parent_id：丧失树形语义 → 拒绝
- XML 格式：与 JSON API 不一致 → 拒绝

---

