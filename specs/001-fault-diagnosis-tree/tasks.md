# Tasks: 智能故障诊断与故障树生成系统

**Input**: Design documents from `/specs/001-fault-diagnosis-tree/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Not explicitly requested — test tasks are NOT included. Add test phases if TDD is desired.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths included in all descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add new dependencies and create directory scaffolding for the feature

- [x] T001 Add new dependencies (sqlalchemy, alembic, psycopg2-binary) to requirements.txt
- [x] T002 Create new directory structure with __init__.py files for Backend/Infrastructure/persistence/, Backend/Infrastructure/persistence/models/, Backend/Infrastructure/skill/, Backend/Infrastructure/file/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Domain model, Protocol interfaces, database layer, and Alembic migrations that MUST be complete before user story implementation

**⚠️ CRITICAL**: US2, US3, US4 cannot begin until this phase is complete. US1 can start after Phase 1.

### Domain Enums

- [x] T003 [P] Create SessionStatus enum (in_progress, tree_generated, completed) in Backend/Domain/Common/Enums/session_status.py
- [x] T004 [P] Create MessageRole enum (user, assistant) in Backend/Domain/Common/Enums/message_role.py
- [x] T005 [P] Create FaultTreeStatus enum (draft, confirmed, standardized, failed_standardization) in Backend/Domain/Common/Enums/fault_tree_status.py
- [x] T006 [P] Create NodeType enum (basic_event, intermediate_event, undeveloped_event, external_event, conditional_event) in Backend/Domain/Common/Enums/node_type.py
- [x] T007 [P] Create GateType enum (AND, OR, XOR, INHIBIT, PRIORITY_AND) in Backend/Domain/Common/Enums/gate_type.py

### Domain Entities (Aggregate Roots)

- [x] T008 [P] Create DiagnosisSession aggregate root and ChatMessage entity as pure Python dataclasses with invariant enforcement in Backend/Domain/Entities/diagnosis_session.py
- [x] T009 [P] Create FaultTree aggregate root and FaultTreeNode entity as pure Python dataclasses with tree structure validation in Backend/Domain/Entities/fault_tree.py

### Application Protocol Interfaces (Shared)

- [x] T010 [P] Create SessionRepository Protocol (save, find_by_id) in Backend/Application/Interfaces/session_repository.py
- [x] T011 [P] Create FaultTreeRepository Protocol (save, find_by_id) in Backend/Application/Interfaces/fault_tree_repository.py

### PostgreSQL Persistence Layer

- [x] T012 Configure SQLAlchemy engine, declarative Base, and scoped session factory in Backend/Infrastructure/persistence/database.py
- [x] T013 [P] Create diagnosis_sessions and chat_messages ORM table models (Data Mapper pattern) in Backend/Infrastructure/persistence/models/session_model.py
- [x] T014 [P] Create fault_trees ORM table model with JSONB tree_data column in Backend/Infrastructure/persistence/models/fault_tree_model.py
- [x] T015 Setup Alembic configuration (alembic.ini, env.py) and generate initial migration for all three tables in alembic/
- [x] T016 [P] Create .env.example with DATABASE_URL, DEEPSEEK_API_KEY, and CHROMA_PERSIST_DIR configuration

**Checkpoint**: Foundation ready — Domain model defined, database schema in place, Protocol contracts established. User story implementation can now begin.

---

## Phase 3: User Story 1 — 知识库文档上传与向量化 (Priority: P1) 🎯 MVP

**Goal**: Upload PDF documents with automatic chunking, deduplication (hash + metadata + embedding similarity), and vectorization into ChromaDB.

**Independent Test**: Upload a PDF via `POST /api/documents/upload`, verify response includes chunk statistics with deduplication counts; query ChromaDB to confirm chunks are retrievable.

**FR Coverage**: FR-001, FR-002, FR-003, FR-004, FR-005

> **Note**: US1 depends only on Phase 1 (Setup). It does NOT require Phase 2 (PostgreSQL). Can start in parallel with Phase 2.

### Implementation for User Story 1

- [x] T017 [P] [US1] Create DocumentDeduplicator Protocol (deduplicate method accepting chunks and existing hashes) in Backend/Application/Interfaces/document_deduplicator.py
- [x] T018 [US1] Implement three-tier deduplicator (SHA-256 hash → metadata comparison → embedding cosine similarity > 0.95) in Backend/Infrastructure/document/deduplicator.py
- [x] T019 [US1] Refactor upload_pdf_use_case.py into UploadDocumentUseCase with deduplication pipeline integration in Backend/Application/UseCases/upload_document_use_case.py
- [x] T020 [US1] Create document upload endpoint (POST /api/documents/upload, multipart/form-data) in Backend/Web/Endpoints/documents.py
- [x] T021 [US1] Register document_endpoints blueprint and wire UploadDocumentUseCase dependencies in Backend/Web/app_factory.py

**Checkpoint**: User Story 1 complete — document upload with deduplication is functional and independently testable.

---

## Phase 4: User Story 2 — 多轮对话式故障诊断 (Priority: P2)

**Goal**: Create diagnosis sessions with multi-turn RAG-powered dialogue. System performs intent classification, retrieves relevant knowledge base documents, generates guided diagnostic questions, and tracks conversation history in PostgreSQL.

**Independent Test**: Create a session via `POST /api/diagnosis/sessions` with an initial fault description, verify AI reply with clarifying questions; continue dialogue via `POST /api/diagnosis/sessions/{id}/messages`, verify knowledge-based responses and `diagnosis_sufficient` flag after adequate rounds.

**FR Coverage**: FR-006, FR-007, FR-008, FR-009, FR-010, FR-011

**Dependencies**: Requires Phase 2 (Foundational) complete

### Implementation for User Story 2

- [x] T022 [P] [US2] Create DiagnosisLlmClient Protocol (diagnose, classify_intent, assess_sufficiency methods) in Backend/Application/Interfaces/diagnosis_llm_client.py
- [x] T023 [US2] Implement DiagnosisLlmAdapter using DeepSeek for intent classification, sufficiency assessment, and RAG-augmented diagnosis in Backend/Infrastructure/llm/diagnosis_llm_adapter.py
- [x] T024 [US2] Implement PgSessionRepository with save and find_by_id (eager-load messages) in Backend/Infrastructure/persistence/pg_session_repository.py
- [x] T025 [P] [US2] Create CreateSessionUseCase (create session, run initial RAG diagnosis, persist) in Backend/Application/UseCases/create_session_use_case.py
- [x] T026 [US2] Create DiagnoseUseCase (load session, validate session status, RAG retrieval, LLM with conversation history, intent check, sufficiency assessment, persist) in Backend/Application/UseCases/diagnose_use_case.py
- [x] T027 [P] [US2] Create GetSessionUseCase (load session with full message history) in Backend/Application/UseCases/get_session_use_case.py
- [x] T028 [US2] Create diagnosis endpoints (POST /api/diagnosis/sessions, POST /api/diagnosis/sessions/{id}/messages, GET /api/diagnosis/sessions/{id}) in Backend/Web/Endpoints/diagnosis.py
- [x] T029 [US2] Register diagnosis_endpoints blueprint and wire all diagnosis dependencies (PgSessionRepository, DiagnosisLlmAdapter, RetrieverFactory) in Backend/Web/app_factory.py

**Checkpoint**: User Stories 1 + 2 both independently functional. Knowledge upload and multi-turn diagnosis work end-to-end.

---

## Phase 5: User Story 3 — 故障树生成 (Priority: P3)

**Goal**: Generate fault trees from diagnosis session dialogue via a Skill interface stub. The stub returns a mock fault tree JSON following the simplified IEC 61025 schema (R-006). Real Skill implementation to be provided later.

**Independent Test**: After completing a diagnosis session (US2), call `POST /api/fault-trees/generate` with the session_id, verify returned fault tree JSON contains valid node structure (root → intermediate → basic events); call `GET /api/fault-trees/{id}` to verify persistence.

**FR Coverage**: FR-012, FR-013, FR-014, FR-015

**Dependencies**: Requires Phase 4 (US2) — needs PgSessionRepository and session data

### Implementation for User Story 3

- [ ] T030 [P] [US3] Create FaultTreeGenerationSkill Protocol (generate, get_missing_info methods) in Backend/Application/Interfaces/fault_tree_skill.py
- [ ] T031 [P] [US3] Implement StubFaultTreeSkill returning mock fault tree JSON with configurable structure in Backend/Infrastructure/skill/stub_fault_tree_skill.py
- [ ] T032 [US3] Implement PgFaultTreeRepository with save (serialize tree to JSONB), find_by_id (deserialize JSONB to domain entity) in Backend/Infrastructure/persistence/pg_fault_tree_repository.py
- [ ] T033 [US3] Create GenerateFaultTreeUseCase (load session, invoke skill, handle insufficient info, persist fault tree, link to session) in Backend/Application/UseCases/generate_fault_tree_use_case.py
- [ ] T034 [P] [US3] Create GetFaultTreeUseCase (load and return fault tree by ID) in Backend/Application/UseCases/get_fault_tree_use_case.py
- [ ] T035 [US3] Create fault tree endpoints (POST /api/fault-trees/generate, GET /api/fault-trees/{id}) in Backend/Web/Endpoints/fault_trees.py
- [ ] T036 [US3] Register fault_tree_endpoints blueprint and wire fault tree dependencies (PgFaultTreeRepository, StubFaultTreeSkill, PgSessionRepository) in Backend/Web/app_factory.py

**Checkpoint**: User Stories 1 + 2 + 3 functional. Full flow from document upload → diagnosis → fault tree generation works end-to-end.

---

## Phase 6: User Story 4 — 人工校准与案例入库 (Priority: P4)

**Goal**: Allow users to review and modify generated fault trees, then confirm them as cases. On confirmation: persist to PostgreSQL, generate a plain-text case file, vectorize case text into ChromaDB for similarity retrieval, and invoke the standardization Skill stub.

**Independent Test**: Given an existing fault tree in `draft` status, call `PUT /api/fault-trees/{id}` to modify nodes and verify structural validation; call `POST /api/cases/confirm` and verify fault tree status transitions to `confirmed`, text file is generated, and standardization is attempted (stub returns success).

**FR Coverage**: FR-016, FR-017, FR-018, FR-019, FR-020, FR-021

**Dependencies**: Requires Phase 5 (US3) — needs fault tree to exist

### Implementation for User Story 4

- [ ] T037 [P] [US4] Create CaseStandardizationSkill Protocol (standardize method) in Backend/Application/Interfaces/case_standardization_skill.py
- [ ] T038 [P] [US4] Create CaseTextFileWriter Protocol (write method returning file path) in Backend/Application/Interfaces/case_file_writer.py
- [ ] T039 [P] [US4] Implement StubCaseStandardizationSkill (always returns success) in Backend/Infrastructure/skill/stub_case_standardization.py
- [ ] T040 [P] [US4] Implement CaseTextFileWriter (serialize fault tree to human-readable text file) in Backend/Infrastructure/file/case_text_writer.py
- [ ] T041 [US4] Create UpdateFaultTreeUseCase (validate tree structure invariants, save modifications) in Backend/Application/UseCases/update_fault_tree_use_case.py
- [ ] T042 [US4] Create ConfirmCaseUseCase (confirm fault tree, write text file, vectorize to ChromaDB, invoke standardization skill, handle failure gracefully per FR-021) in Backend/Application/UseCases/confirm_case_use_case.py
- [ ] T043 [US4] Add PUT /api/fault-trees/{id} endpoint for fault tree modification with structure validation in Backend/Web/Endpoints/fault_trees.py
- [ ] T044 [US4] Create case confirmation endpoint (POST /api/cases/confirm) in Backend/Web/Endpoints/cases.py
- [ ] T045 [US4] Register case_endpoints blueprint and wire case dependencies (PgFaultTreeRepository, StubCaseStandardizationSkill, CaseTextFileWriter, VectorStoreRepository) in Backend/Web/app_factory.py

**Checkpoint**: All four user stories complete. Full closed-loop: upload → diagnose → generate fault tree → review → archive as case.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, cleanup, and cross-cutting improvements

- [ ] T046 Validate all __init__.py exports are correct for new modules across Backend/
- [ ] T047 Run quickstart.md end-to-end smoke test (6-step validation flow) and fix any integration issues

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ─────┬──→ Phase 2 (Foundational) ──→ Phase 4 (US2) ──→ Phase 5 (US3) ──→ Phase 6 (US4) ──→ Phase 7 (Polish)
                      │
                      └──→ Phase 3 (US1) ─────────────────────────────────────────────────→ Phase 7 (Polish)
```

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS US2, US3, US4
- **US1 (Phase 3)**: Depends on Phase 1 ONLY — can run in parallel with Phase 2
- **US2 (Phase 4)**: Depends on Phase 2 completion
- **US3 (Phase 5)**: Depends on US2 (Phase 4) — needs PgSessionRepository and session data
- **US4 (Phase 6)**: Depends on US3 (Phase 5) — needs fault tree to exist
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

| Story | Depends On | Can Start After |
|-------|-----------|-----------------|
| US1 (P1) | Phase 1 only | Phase 1 ✅ |
| US2 (P2) | Phase 2 (Foundational) | Phase 2 ✅ |
| US3 (P3) | US2 (needs SessionRepository impl + session data) | Phase 4 ✅ |
| US4 (P4) | US3 (needs FaultTreeRepository impl + fault tree data) | Phase 5 ✅ |

### Within Each User Story

1. Protocols before implementations
2. Infrastructure (repositories, adapters) before Use Cases
3. Use Cases before Endpoints
4. Endpoints before app_factory wiring
5. Story complete at checkpoint before moving to next priority

### Parallel Opportunities

**Phase 2 parallelism**:
- T003 through T007 (5 enum files) — all [P]
- T008 and T009 (2 entity files) — both [P] with each other
- T010 and T011 (2 Protocol files) — both [P]
- T013 and T014 (2 ORM model files) — both [P]

**Inter-phase parallelism**:
- Phase 3 (US1) can run entirely in parallel with Phase 2
- This means a developer can work on US1 deduplication while another sets up the database

**Within US4**:
- T037, T038, T039, T040 — all four Protocol/implementation files are [P]

---

## Parallel Example: Phase 2 (Foundational)

```text
# Batch 1 — All enums in parallel:
T003: SessionStatus enum
T004: MessageRole enum
T005: FaultTreeStatus enum
T006: NodeType enum
T007: GateType enum

# Batch 2 — Both entities + both Protocols in parallel:
T008: DiagnosisSession entity
T009: FaultTree entity
T010: SessionRepository Protocol
T011: FaultTreeRepository Protocol

# Batch 3 — Database + env in parallel:
T012: database.py (SQLAlchemy setup)
T016: .env.example

# Batch 4 — Both ORM models in parallel:
T013: session_model.py
T014: fault_tree_model.py

# Batch 5 — Sequential:
T015: Alembic setup + migration
```

## Parallel Example: US1 + Phase 2 in parallel

```text
# Developer A: Phase 2 (Foundational)
T003→T007 → T008→T011 → T012→T016 → T013→T014 → T015

# Developer B: Phase 3 (US1) — independent of PostgreSQL
T017 → T018 → T019 → T020 → T021
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 3: User Story 1 (can skip Phase 2 entirely for MVP)
3. **STOP and VALIDATE**: Upload a PDF, verify deduplication stats
4. Deploy/demo if ready — knowledge base is functional

### Incremental Delivery

1. Phase 1 (Setup) → Phase 3 (US1) → **MVP: Knowledge base upload works** ✅
2. Phase 2 (Foundational) → Phase 4 (US2) → **Increment: Diagnosis dialogues work** ✅
3. Phase 5 (US3) → **Increment: Fault tree generation works** ✅
4. Phase 6 (US4) → **Increment: Full closed-loop with case archival** ✅
5. Phase 7 (Polish) → **Final: Validated, clean, production-ready**

Each increment adds value without breaking previous stories.

### Sequential Execution (Single Developer)

T001 → T002 → T003...T007 → T008...T011 → T012 → T013...T014 → T015 → T016 → T017...T021 → T022...T029 → T030...T036 → T037...T045 → T046 → T047

---

## Notes

- All Domain entities are pure Python dataclasses — NO framework dependencies (Constitution Principle I)
- All Use Cases depend on Protocol interfaces via constructor injection (Constitution Principle VI)
- ORM models in Infrastructure layer are separate from Domain entities (Data Mapper pattern per R-001)
- Skill modules (FaultTreeGenerationSkill, CaseStandardizationSkill) are stubs — real implementations to be provided by separate teams
- PostgreSQL = source of truth (ACID); ChromaDB = vector retrieval optimization (R-002)
- Conversation history managed manually in Application layer, not via LangChain Memory (R-005)
