# Data Model: 智能故障诊断与故障树生成系统

**Date**: 2026-03-24  
**Feature**: 001-fault-diagnosis-tree  
**Research**: [research.md](research.md) — R-003, R-006

---

## Aggregate 1: DiagnosisSession（诊断会话聚合）

> **聚合根**: `DiagnosisSession`  
> **存储**: PostgreSQL（结构化持久存储）  
> **层级**: Domain 层 — `Backend/Domain/Entities/`

### DiagnosisSession（聚合根）

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | `str (UUID)` | 会话唯一标识 | PK, 不可变 |
| created_at | `datetime` | 创建时间 | 不可变, UTC |
| updated_at | `datetime` | 最后活动时间 | 每次操作更新 |
| status | `SessionStatus` | 会话状态 | 枚举值, 合法转换 |
| messages | `list[ChatMessage]` | 对话消息列表 | 有序, 只追加 |
| fault_tree_id | `str (UUID) | None` | 关联故障树 ID | 生成故障树后设置 |

**不变量 (Invariants)**:
- 消息列表 MUST 按时间顺序排列
- 状态转换 MUST 遵循合法路径（见状态机）
- 已完成的会话 MUST NOT 追加新消息
- fault_tree_id 仅在状态为 `tree_generated` 或 `completed` 时非空

### ChatMessage（实体 — 属于 DiagnosisSession 聚合）

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | `str (UUID)` | 消息唯一标识 | PK, 不可变 |
| role | `MessageRole` | 消息角色 | 枚举: user / assistant |
| content | `str` | 消息文本内容 | 非空 |
| created_at | `datetime` | 发送时间 | 不可变, UTC |

### SessionStatus（值对象 — 枚举）

```
in_progress  →  tree_generated  →  completed
```

| Value | Description | 可转入状态 |
|-------|-------------|-----------|
| `in_progress` | 对话进行中 | `tree_generated` |
| `tree_generated` | 已生成故障树，待确认 | `completed`, `in_progress`(继续补充) |
| `completed` | 用户确认故障树，会话完成 | — (终态) |

### MessageRole（值对象 — 枚举）

| Value | Description |
|-------|-------------|
| `user` | 用户发送的消息 |
| `assistant` | 系统/AI 回复的消息 |

---

## Aggregate 2: FaultTree（故障树聚合）

> **聚合根**: `FaultTree`  
> **存储**: PostgreSQL（JSON 存储） + ChromaDB（案例文本向量化）  
> **层级**: Domain 层 — `Backend/Domain/Entities/`

### FaultTree（聚合根）

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | `str (UUID)` | 故障树唯一标识 | PK, 不可变 |
| name | `str` | 故障树名称 | 非空 |
| description | `str` | 故障描述摘要 | 非空 |
| session_id | `str (UUID)` | 关联诊断会话 ID | FK 引用, 不可变 |
| root_node | `FaultTreeNode` | 根节点 | 非空, 树形结构 |
| status | `FaultTreeStatus` | 故障树状态 | 枚举值, 合法转换 |
| created_at | `datetime` | 创建时间 | 不可变, UTC |
| confirmed_at | `datetime | None` | 用户确认时间 | 确认时设置 |

**不变量 (Invariants)**:
- root_node MUST NOT 为空
- 树结构 MUST 无环（DAG）
- 每个节点 MUST 有唯一 ID
- `confirmed_at` 仅在 status 为 `confirmed` 或 `standardized` 时非空
- session_id MUST 指向一个已存在的 DiagnosisSession

### FaultTreeNode（实体 — 递归树结构，属于 FaultTree 聚合）

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | `str (UUID)` | 节点唯一标识 | PK, 不可变 |
| name | `str` | 节点名称 | 非空 |
| type | `NodeType` | 节点类型 | 枚举值 |
| gate_type | `GateType | None` | 逻辑门类型 | 仅中间事件需要 |
| description | `str` | 节点描述 | 可选 |
| children | `list[FaultTreeNode]` | 子节点列表 | 递归, 叶子节点为空列表 |

**不变量 (Invariants)**:
- `basic_event` 类型节点 MUST 无子节点（叶子节点）
- `intermediate_event` 类型节点 MUST 有 gate_type 且 MUST 有至少一个子节点
- `undeveloped_event` 类型节点 MUST 无子节点

### FaultTreeStatus（值对象 — 枚举）

```
draft  →  confirmed  →  standardized
               ↓              ↓
            draft (退回修改)  failed_standardization
```

| Value | Description | 可转入状态 |
|-------|-------------|-----------|
| `draft` | 系统生成，待用户审阅 | `confirmed` |
| `confirmed` | 用户确认，待标准化 | `standardized`, `failed_standardization`, `draft` |
| `standardized` | 标准化完成，已入库 | — (终态) |
| `failed_standardization` | 标准化失败，原始数据已保存 | `confirmed`(重试) |

### NodeType（值对象 — 枚举）

| Value | Description |
|-------|-------------|
| `basic_event` | 基本事件（叶子节点，不可再分解的原因） |
| `intermediate_event` | 中间事件（带逻辑门的非叶子节点） |
| `undeveloped_event` | 未展开事件（信息不足，待后续细化） |
| `external_event` | 外部事件（系统外部原因） |
| `conditional_event` | 条件事件（在特定条件下触发） |

### GateType（值对象 — 枚举）

| Value | Description |
|-------|-------------|
| `AND` | 所有子事件同时发生时触发 |
| `OR` | 任一子事件发生时触发 |
| `XOR` | 恰好一个子事件发生时触发 |
| `INHIBIT` | 输入事件 + 条件都满足时触发 |
| `PRIORITY_AND` | 子事件按特定顺序发生时触发 |

---

## Domain Entity Location Map

> 所有 Domain 实体为纯 Python dataclass, MUST NOT 依赖任何外部框架

```
Backend/Domain/
├── Entities/
│   ├── diagnosis_session.py      # DiagnosisSession 聚合根 + ChatMessage
│   └── fault_tree.py             # FaultTree 聚合根 + FaultTreeNode
├── Common/
│   ├── Enums/
│   │   ├── session_status.py     # SessionStatus 枚举
│   │   ├── message_role.py       # MessageRole 枚举
│   │   ├── fault_tree_status.py  # FaultTreeStatus 枚举
│   │   ├── node_type.py          # NodeType 枚举
│   │   └── gate_type.py          # GateType 枚举
│   └── Models/
│       └── (reserved)
```

---

## Relationship Diagram

```
┌─────────────────────────────────────┐
│  DiagnosisSession (Aggregate Root)  │
│  ─────────────────────────────────  │
│  id: UUID                           │
│  status: SessionStatus              │
│  fault_tree_id: UUID | None ────────┼────────┐
│  messages: list[ChatMessage]        │        │
│    ├── ChatMessage                  │        │
│    ├── ChatMessage                  │        │
│    └── ...                          │        │
└─────────────────────────────────────┘        │
                                               │
                                       (by ID reference)
                                               │
┌─────────────────────────────────────┐        │
│     FaultTree (Aggregate Root)      │◄───────┘
│  ─────────────────────────────────  │
│  id: UUID                           │
│  session_id: UUID                   │
│  status: FaultTreeStatus            │
│  root_node: FaultTreeNode           │
│    ├── FaultTreeNode (intermediate) │
│    │   ├── FaultTreeNode (basic)    │
│    │   └── FaultTreeNode (basic)    │
│    └── FaultTreeNode (undeveloped)  │
└─────────────────────────────────────┘
```

---

## Storage Schema (PostgreSQL)

> Infrastructure 层 ORM 映射，与 Domain 实体分离（Data Mapper 模式）

### Table: `diagnosis_sessions`

| Column | Type | Notes |
|--------|------|-------|
| id | `UUID` | PK |
| status | `VARCHAR(30)` | 枚举字符串 |
| fault_tree_id | `UUID` | FK → fault_trees.id, NULLABLE |
| created_at | `TIMESTAMP WITH TIME ZONE` | NOT NULL |
| updated_at | `TIMESTAMP WITH TIME ZONE` | NOT NULL |

### Table: `chat_messages`

| Column | Type | Notes |
|--------|------|-------|
| id | `UUID` | PK |
| session_id | `UUID` | FK → diagnosis_sessions.id, NOT NULL |
| role | `VARCHAR(20)` | 'user' / 'assistant' |
| content | `TEXT` | NOT NULL |
| created_at | `TIMESTAMP WITH TIME ZONE` | NOT NULL |

**Index**: `idx_messages_session_created` on `(session_id, created_at)`

### Table: `fault_trees`

| Column | Type | Notes |
|--------|------|-------|
| id | `UUID` | PK |
| name | `VARCHAR(255)` | NOT NULL |
| description | `TEXT` | NOT NULL |
| session_id | `UUID` | FK → diagnosis_sessions.id, NOT NULL |
| tree_data | `JSONB` | 完整故障树 JSON（含所有节点） |
| status | `VARCHAR(30)` | 枚举字符串 |
| created_at | `TIMESTAMP WITH TIME ZONE` | NOT NULL |
| confirmed_at | `TIMESTAMP WITH TIME ZONE` | NULLABLE |

**Index**: `idx_fault_trees_session` on `(session_id)`  
**Index**: `idx_fault_trees_status` on `(status)`

---

## Fault Tree JSON Example (stored in `tree_data` JSONB column)

```json
{
  "id": "node-root-001",
  "name": "电机轴承过热",
  "type": "intermediate_event",
  "gate_type": "OR",
  "description": "电机运行时轴承温度超过85°C",
  "children": [
    {
      "id": "node-mid-001",
      "name": "润滑不良",
      "type": "intermediate_event",
      "gate_type": "AND",
      "description": "润滑系统故障导致轴承缺油",
      "children": [
        {
          "id": "node-leaf-001",
          "name": "润滑油不足",
          "type": "basic_event",
          "gate_type": null,
          "description": "油位低于最低刻度线",
          "children": []
        },
        {
          "id": "node-leaf-002",
          "name": "油路堵塞",
          "type": "basic_event",
          "gate_type": null,
          "description": "润滑油管路存在杂质堵塞",
          "children": []
        }
      ]
    },
    {
      "id": "node-leaf-003",
      "name": "轴承磨损",
      "type": "basic_event",
      "gate_type": null,
      "description": "轴承运行超过设计寿命，内圈磨损严重",
      "children": []
    },
    {
      "id": "node-mid-002",
      "name": "外部环境因素",
      "type": "undeveloped_event",
      "gate_type": null,
      "description": "环境温度过高等外部因素（待进一步分析）",
      "children": []
    }
  ]
}
```
