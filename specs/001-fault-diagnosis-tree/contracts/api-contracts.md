# API Contracts: 智能故障诊断与故障树生成系统

**Date**: 2026-03-24  
**Feature**: 001-fault-diagnosis-tree  
**Base URL**: `http://{host}:8080`

---

## Blueprint 总览

| Blueprint | URL Prefix | 职责 | Use Case |
|-----------|------------|------|----------|
| `document_endpoints` | `/api/documents` | 知识库文档管理 | `UploadDocumentUseCase` |
| `diagnosis_endpoints` | `/api/diagnosis` | 诊断会话管理 & 多轮对话 | `CreateSessionUseCase`, `DiagnoseUseCase` |
| `fault_tree_endpoints` | `/api/fault-trees` | 故障树生成 & 管理 | `GenerateFaultTreeUseCase`, `UpdateFaultTreeUseCase` |
| `case_endpoints` | `/api/cases` | 案例确认 & 入库 | `ConfirmCaseUseCase` |

> 每个 Blueprint 对应一个独立文件（SRP），仅做 HTTP ↔ Use Case 的适配

---

## 1. Document Endpoints — 知识库文档管理

### POST /api/documents/upload

**职责**: 上传文档，执行切分、清洗去重和向量化入库

**Blueprint**: `document_endpoints`  
**Use Case**: `UploadDocumentUseCase`  
**FR Coverage**: FR-001, FR-002, FR-003, FR-004, FR-005

**Request**:
```
Content-Type: multipart/form-data

file: <binary>  (required, PDF file)
```

**Response 200**:
```json
{
  "status": "success",
  "filename": "maintenance_manual.pdf",
  "total_chunks": 45,
  "persisted_chunks": 38,
  "deduplicated_chunks": 7,
  "skipped_chunks": 0
}
```

**Response 400**:
```json
{
  "status": "error",
  "message": "Unsupported file format. Only PDF is supported."
}
```

**Response 500**:
```json
{
  "status": "error",
  "message": "Internal processing error"
}
```

---

## 2. Diagnosis Endpoints — 诊断会话管理 & 多轮对话

### POST /api/diagnosis/sessions

**职责**: 创建新的诊断会话

**Blueprint**: `diagnosis_endpoints`  
**Use Case**: `CreateSessionUseCase`  
**FR Coverage**: FR-006, FR-010

**Request**:
```json
{
  "initial_message": "设备启动后温度异常升高"
}
```

**Response 201**:
```json
{
  "session_id": "uuid-session-001",
  "status": "in_progress",
  "created_at": "2026-03-24T10:00:00Z",
  "reply": {
    "role": "assistant",
    "content": "您好，我注意到您提到了设备温度异常。为了更好地诊断，请问：\n1. 是哪台设备出现了温度异常？\n2. 温度大约升高到了多少度？\n3. 这个情况是什么时候开始的？",
    "intent": "fault_diagnosis"
  }
}
```

> 创建会话时同步执行首轮对话（意图识别 + RAG 检索 + LLM 生成追问）

---

### POST /api/diagnosis/sessions/{session_id}/messages

**职责**: 在现有会话中追加消息，执行多轮诊断对话

**Blueprint**: `diagnosis_endpoints`  
**Use Case**: `DiagnoseUseCase`  
**FR Coverage**: FR-007, FR-008, FR-009, FR-010, FR-011

**Path Parameter**:
- `session_id` (UUID) — 诊断会话 ID

**Request**:
```json
{
  "message": "是3号电机，温度升到了85度以上，从昨天下午开始的"
}
```

**Response 200** (正常诊断中):
```json
{
  "session_id": "uuid-session-001",
  "status": "in_progress",
  "reply": {
    "role": "assistant",
    "content": "感谢您的信息。根据知识库中的维修手册，3号电机温度超过85°C可能与以下原因有关：\n1. 轴承润滑不足\n2. 冷却系统故障\n请问您是否检查过润滑油位和冷却水流量？",
    "intent": "fault_diagnosis"
  },
  "sources": [
    {
      "source": "motor_maintenance_v2.pdf",
      "page_content": "当电机温度超过80°C时..."
    }
  ],
  "diagnosis_sufficient": false
}
```

**Response 200** (信息充足，建议生成故障树):
```json
{
  "session_id": "uuid-session-001",
  "status": "in_progress",
  "reply": {
    "role": "assistant",
    "content": "根据目前收集的信息，我已经对故障原因有了较全面的了解。建议现在生成故障树进行结构化分析。是否需要我为您生成故障树？",
    "intent": "suggest_fault_tree"
  },
  "sources": [],
  "diagnosis_sufficient": true
}
```

**Response 200** (非故障诊断意图):
```json
{
  "session_id": "uuid-session-001",
  "status": "in_progress",
  "reply": {
    "role": "assistant",
    "content": "我是故障诊断助手，专注于帮助您分析设备故障。请描述您遇到的设备问题，我会帮您进行诊断。",
    "intent": "off_topic"
  },
  "sources": [],
  "diagnosis_sufficient": false
}
```

**Response 404**:
```json
{
  "status": "error",
  "message": "Session not found"
}
```

**Response 409**:
```json
{
  "status": "error",
  "message": "Session is already completed"
}
```

---

### GET /api/diagnosis/sessions/{session_id}

**职责**: 查询会话详情（含完整对话历史）

**Blueprint**: `diagnosis_endpoints`  
**Use Case**: `GetSessionUseCase`  
**FR Coverage**: FR-010

**Response 200**:
```json
{
  "session_id": "uuid-session-001",
  "status": "in_progress",
  "created_at": "2026-03-24T10:00:00Z",
  "updated_at": "2026-03-24T10:05:00Z",
  "fault_tree_id": null,
  "messages": [
    {
      "id": "msg-001",
      "role": "user",
      "content": "设备启动后温度异常升高",
      "created_at": "2026-03-24T10:00:00Z"
    },
    {
      "id": "msg-002",
      "role": "assistant",
      "content": "您好，我注意到您提到了设备温度异常...",
      "created_at": "2026-03-24T10:00:01Z"
    }
  ]
}
```

---

## 3. Fault Tree Endpoints — 故障树生成 & 管理

### POST /api/fault-trees/generate

**职责**: 根据诊断会话语料调用 Skill 接口生成故障树

**Blueprint**: `fault_tree_endpoints`  
**Use Case**: `GenerateFaultTreeUseCase`  
**FR Coverage**: FR-012, FR-013, FR-014, FR-015

**Request**:
```json
{
  "session_id": "uuid-session-001"
}
```

**Response 201** (生成成功):
```json
{
  "fault_tree": {
    "id": "ft-uuid-001",
    "name": "3号电机轴承过热故障树",
    "description": "3号电机运行时轴承温度超过85°C的故障分析",
    "session_id": "uuid-session-001",
    "status": "draft",
    "created_at": "2026-03-24T10:10:00Z",
    "root": {
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
          "description": "润滑系统故障",
          "children": [
            {
              "id": "node-leaf-001",
              "name": "润滑油不足",
              "type": "basic_event",
              "gate_type": null,
              "description": "油位低于最低刻度线",
              "children": []
            }
          ]
        }
      ]
    }
  }
}
```

**Response 422** (信息不足):
```json
{
  "status": "insufficient_info",
  "message": "诊断信息不足，无法生成完整故障树",
  "missing_info": [
    "故障发生的具体设备型号",
    "故障前是否有异常声响"
  ]
}
```

**Response 404**:
```json
{
  "status": "error",
  "message": "Session not found"
}
```

---

### GET /api/fault-trees/{fault_tree_id}

**职责**: 查询故障树详情

**Blueprint**: `fault_tree_endpoints`  
**Use Case**: `GetFaultTreeUseCase`  

**Response 200**: 同 POST generate 成功的 `fault_tree` 结构

---

### PUT /api/fault-trees/{fault_tree_id}

**职责**: 用户修改故障树（人工校准）

**Blueprint**: `fault_tree_endpoints`  
**Use Case**: `UpdateFaultTreeUseCase`  
**FR Coverage**: FR-016, FR-017

**Request**:
```json
{
  "name": "3号电机轴承过热故障树（修订版）",
  "description": "更新后的故障分析",
  "root": {
    "id": "node-root-001",
    "name": "电机轴承过热",
    "type": "intermediate_event",
    "gate_type": "OR",
    "description": "电机运行时轴承温度超过85°C",
    "children": ["...（完整树结构）"]
  }
}
```

**Response 200**:
```json
{
  "fault_tree": {
    "id": "ft-uuid-001",
    "status": "draft",
    "...": "（完整故障树结构）"
  }
}
```

**Response 400** (结构校验失败):
```json
{
  "status": "error",
  "message": "Invalid fault tree structure",
  "errors": [
    "Node node-mid-001: intermediate_event must have gate_type",
    "Node node-leaf-005: basic_event must not have children"
  ]
}
```

---

## 4. Case Endpoints — 案例确认 & 入库

### POST /api/cases/confirm

**职责**: 用户确认故障树为案例，触发持久化和标准化流程

**Blueprint**: `case_endpoints`  
**Use Case**: `ConfirmCaseUseCase`  
**FR Coverage**: FR-018, FR-019, FR-020, FR-021

**Request**:
```json
{
  "fault_tree_id": "ft-uuid-001"
}
```

**Response 200** (入库成功):
```json
{
  "fault_tree_id": "ft-uuid-001",
  "status": "confirmed",
  "confirmed_at": "2026-03-24T10:15:00Z",
  "text_file_generated": true,
  "standardization": {
    "status": "success",
    "message": "案例已成功标准化并入库"
  }
}
```

**Response 200** (入库成功但标准化失败):
```json
{
  "fault_tree_id": "ft-uuid-001",
  "status": "confirmed",
  "confirmed_at": "2026-03-24T10:15:00Z",
  "text_file_generated": true,
  "standardization": {
    "status": "failed",
    "message": "标准化处理失败，案例原始数据已安全保存。可稍后重试。"
  }
}
```

**Response 400**:
```json
{
  "status": "error",
  "message": "Fault tree is not in draft status"
}
```

**Response 404**:
```json
{
  "status": "error",
  "message": "Fault tree not found"
}
```

---

## Protocol Interfaces (Application Layer)

> 以下 Protocol 定义于 `Backend/Application/Interfaces/`，与上述 API 契约对应

### 新增 Protocol 文件清单

| Protocol | File | 消费者 (Use Case) |
|----------|------|-------------------|
| `SessionRepository` | `session_repository.py` | CreateSession, Diagnose, GetSession |
| `FaultTreeRepository` | `fault_tree_repository.py` | GenerateFaultTree, UpdateFaultTree, GetFaultTree, ConfirmCase |
| `FaultTreeGenerationSkill` | `fault_tree_skill.py` | GenerateFaultTreeUseCase |
| `CaseStandardizationSkill` | `case_standardization_skill.py` | ConfirmCaseUseCase |
| `CaseTextFileWriter` | `case_file_writer.py` | ConfirmCaseUseCase |
| `DiagnosisLlmClient` | `diagnosis_llm_client.py` | DiagnoseUseCase |
| `DocumentDeduplicator` | `document_deduplicator.py` | UploadDocumentUseCase |

### Protocol 方法签名摘要

```python
# session_repository.py
class SessionRepository(Protocol):
    def save(self, session: DiagnosisSession) -> None: ...
    def find_by_id(self, session_id: str) -> DiagnosisSession | None: ...

# fault_tree_repository.py
class FaultTreeRepository(Protocol):
    def save(self, fault_tree: FaultTree) -> None: ...
    def find_by_id(self, fault_tree_id: str) -> FaultTree | None: ...

# fault_tree_skill.py (接口留空 — Skill 模块)
class FaultTreeGenerationSkill(Protocol):
    def generate(self, session: DiagnosisSession) -> FaultTree | None: ...
    def get_missing_info(self, session: DiagnosisSession) -> list[str]: ...

# case_standardization_skill.py (接口留空 — Skill 模块)
class CaseStandardizationSkill(Protocol):
    def standardize(self, fault_tree: FaultTree) -> bool: ...

# case_file_writer.py
class CaseTextFileWriter(Protocol):
    def write(self, fault_tree: FaultTree) -> str: ...  # returns file path

# diagnosis_llm_client.py
class DiagnosisLlmClient(Protocol):
    def diagnose(self, messages: list[ChatMessage], context: str) -> str: ...
    def classify_intent(self, message: str) -> str: ...
    def assess_sufficiency(self, messages: list[ChatMessage]) -> bool: ...

# document_deduplicator.py
class DocumentDeduplicator(Protocol):
    def deduplicate(self, chunks: list, existing_hashes: set[str]) -> tuple[list, int]: ...
```

---

## Use Case File Map

| Use Case | File | 依赖的 Protocol |
|----------|------|-----------------|
| `UploadDocumentUseCase` | `upload_document_use_case.py` | PdfLoader, TextSplitter, VectorStoreRepository, DocumentDeduplicator |
| `CreateSessionUseCase` | `create_session_use_case.py` | SessionRepository, DiagnosisLlmClient, RetrieverFactory |
| `DiagnoseUseCase` | `diagnose_use_case.py` | SessionRepository, DiagnosisLlmClient, RetrieverFactory |
| `GetSessionUseCase` | `get_session_use_case.py` | SessionRepository |
| `GenerateFaultTreeUseCase` | `generate_fault_tree_use_case.py` | SessionRepository, FaultTreeRepository, FaultTreeGenerationSkill |
| `GetFaultTreeUseCase` | `get_fault_tree_use_case.py` | FaultTreeRepository |
| `UpdateFaultTreeUseCase` | `update_fault_tree_use_case.py` | FaultTreeRepository |
| `ConfirmCaseUseCase` | `confirm_case_use_case.py` | FaultTreeRepository, CaseStandardizationSkill, CaseTextFileWriter |
