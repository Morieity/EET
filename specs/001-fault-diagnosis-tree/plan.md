# Implementation Plan: 智能故障诊断与故障树生成系统

**Branch**: `001-fault-diagnosis-tree` | **Date**: 2026-03-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-fault-diagnosis-tree/spec.md`

## Summary

构建基于 RAG 的智能故障诊断系统，通过知识库文档向量化、多轮对话式故障诊断、故障树自动生成（Skill 接口留空）和人工校准案例入库四大功能模块，形成从故障描述到标准化案例的闭环。系统采用整洁架构（Clean Architecture）+ DDD 聚合根设计，双存储方案：PostgreSQL 存储结构化数据（会话、案例），ChromaDB 专注向量检索。

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Flask, LangChain, ChromaDB, SQLAlchemy, Alembic, FastEmbed, DeepSeek (via OpenAI-compatible API)  
**Storage**: PostgreSQL（诊断会话 + 案例结构化存储）, ChromaDB（文档知识库向量检索 + 案例文本向量化）  
**Testing**: pytest  
**Target Platform**: Linux/Windows server  
**Project Type**: web-service  
**Performance Goals**: 文档上传 <2min/50页; 对话响应 <10s; 案例入库 <30s  
**Constraints**: 前端当前不纳入范围; 无用户认证; 仅支持 PDF 格式  
**Scale/Scope**: 单用户/小团队维保场景; 目标知识库 <10000 文档片段

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Check ✅

| Principle | Gate | Status |
|-----------|------|--------|
| I. 整洁架构分层 (NON-NEGOTIABLE) | 新增功能遵循 Domain→Application→Infrastructure→Web 分层 | ✅ PASS |
| II. SRP | 每个 Use Case、Protocol、Blueprint 单一职责 | ✅ PASS |
| III. OCP | Skill 模块通过 Protocol 扩展，不修改现有代码 | ✅ PASS |
| IV. LSP | 所有 Protocol 实现可无感替换 | ✅ PASS |
| V. ISP | Session 读/写、FaultTree 读/写、Skill 生成/标准化分离为独立 Protocol | ✅ PASS |
| VI. DIP (NON-NEGOTIABLE) | Use Case 依赖 Protocol 注入，装配在 app_factory.py | ✅ PASS |
| VII. 有据可依 | 每个新文件有明确的层级归属和 SOLID 依据 | ✅ PASS |

### Post-Phase 1 Re-check ✅

| Principle | Verification | Status |
|-----------|-------------|--------|
| I. 整洁架构分层 | data-model.md: Domain 实体纯 Python dataclass, 无框架依赖 | ✅ PASS |
| II. SRP | contracts/: 8 个 Use Case 各司其职; 7 个 Protocol 接口各定义一组行为 | ✅ PASS |
| III. OCP | FaultTreeGenerationSkill / CaseStandardizationSkill 为 Protocol, 新增实现不改现有代码 | ✅ PASS |
| IV. LSP | SessionRepository 的 PG 实现可替换为任何满足协议的实现 | ✅ PASS |
| V. ISP | SessionRepository (read+write) / FaultTreeRepository (read+write) / VectorStoreRepository (write) / RetrieverFactory (read) 分离 | ✅ PASS |
| VI. DIP | contracts/api-contracts.md: 所有 Use Case 通过构造函数注入 Protocol 类型 | ✅ PASS |
| VII. 有据可依 | Domain Entity Location Map 明确每个文件归属; 目录结构与宪法映射一致 | ✅ PASS |

## Project Structure

### Documentation (this feature)

```text
specs/001-fault-diagnosis-tree/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: Research findings
├── data-model.md        # Phase 1: DDD aggregate roots & data model
├── quickstart.md        # Phase 1: Setup & smoke test guide
├── contracts/
│   └── api-contracts.md # Phase 1: API endpoint definitions
└── tasks.md             # Phase 2 output (by /speckit.tasks)
```

### Source Code (repository root)

```text
Backend/
├── Domain/                              # 领域层（最内层）— 纯 Python, 无框架依赖
│   ├── Entities/
│   │   ├── diagnosis_session.py         # DiagnosisSession 聚合根 + ChatMessage
│   │   ├── fault_tree.py               # FaultTree 聚合根 + FaultTreeNode
│   │   └── Equipment.py                # (existing, empty)
│   └── Common/
│       ├── Enums/
│       │   ├── session_status.py        # SessionStatus 枚举
│       │   ├── message_role.py          # MessageRole 枚举
│       │   ├── fault_tree_status.py     # FaultTreeStatus 枚举
│       │   ├── node_type.py             # NodeType 枚举
│       │   ├── gate_type.py             # GateType 枚举
│       │   └── EquipmentType.py         # (existing, empty)
│       └── Models/
│
├── Application/                         # 应用层 — Use Cases + Protocol 接口
│   ├── Interfaces/
│   │   ├── chat_repository.py           # (existing) ChatClient Protocol
│   │   ├── pdf_repository.py            # (existing) PdfLoader, TextSplitter, VectorStoreRepository
│   │   ├── retriever_repository.py      # (existing) Retriever, RetrieverFactory
│   │   ├── session_repository.py        # NEW: SessionRepository Protocol
│   │   ├── fault_tree_repository.py     # NEW: FaultTreeRepository Protocol
│   │   ├── fault_tree_skill.py          # NEW: FaultTreeGenerationSkill Protocol (留空)
│   │   ├── case_standardization_skill.py# NEW: CaseStandardizationSkill Protocol (留空)
│   │   ├── case_file_writer.py          # NEW: CaseTextFileWriter Protocol
│   │   ├── diagnosis_llm_client.py      # NEW: DiagnosisLlmClient Protocol
│   │   └── document_deduplicator.py     # NEW: DocumentDeduplicator Protocol
│   └── UseCases/
│       ├── ask_pdf_use_case.py          # (existing) RAG 问答
│       ├── chat_use_case.py             # (existing) 简单聊天
│       ├── upload_pdf_use_case.py       # (existing) PDF 上传 → 重构为 UploadDocumentUseCase
│       ├── create_session_use_case.py   # NEW: 创建诊断会话
│       ├── diagnose_use_case.py         # NEW: 多轮诊断对话
│       ├── get_session_use_case.py      # NEW: 查询会话详情
│       ├── generate_fault_tree_use_case.py  # NEW: 生成故障树
│       ├── get_fault_tree_use_case.py   # NEW: 查询故障树
│       ├── update_fault_tree_use_case.py    # NEW: 修改故障树
│       └── confirm_case_use_case.py     # NEW: 确认案例入库
│
├── Infrastructure/                      # 基础设施层 — 技术实现
│   ├── document/
│   │   ├── pdf_loader.py                # (existing) PDFPlumber 加载器
│   │   ├── text_splitter.py             # (existing) 文本分割器
│   │   └── deduplicator.py              # NEW: 文档去重实现（hash + similarity）
│   ├── llm/
│   │   ├── deepseek_client.py           # (existing) DeepSeek LLM 客户端
│   │   └── diagnosis_llm_adapter.py     # NEW: DiagnosisLlmClient 的 DeepSeek 实现
│   ├── vectorstore/
│   │   └── chroma_repository.py         # (existing) ChromaDB 向量存储
│   ├── persistence/                     # NEW: PostgreSQL 持久化
│   │   ├── database.py                  # SQLAlchemy engine + session factory
│   │   ├── models/                      # ORM 映射模型（与 Domain 实体分离）
│   │   │   ├── session_model.py         # diagnosis_sessions + chat_messages 表映射
│   │   │   └── fault_tree_model.py      # fault_trees 表映射
│   │   ├── pg_session_repository.py     # SessionRepository 的 PG 实现
│   │   └── pg_fault_tree_repository.py  # FaultTreeRepository 的 PG 实现
│   ├── skill/                           # NEW: Skill 模块存根实现
│   │   ├── stub_fault_tree_skill.py     # FaultTreeGenerationSkill 存根
│   │   └── stub_case_standardization.py # CaseStandardizationSkill 存根
│   └── file/                            # NEW: 文件输出
│       └── case_text_writer.py          # CaseTextFileWriter 实现
│
└── Web/                                 # 接口适配层（最外层）
    ├── app_factory.py                   # (existing) 组合根 — 依赖装配 (扩展)
    └── Endpoints/
        ├── llmchat.py                   # (existing) POST /chat
        ├── pdfpost.py                   # (existing) POST /pdf
        ├── documents.py                 # NEW: POST /api/documents/upload
        ├── diagnosis.py                 # NEW: /api/diagnosis/* 端点
        ├── fault_trees.py              # NEW: /api/fault-trees/* 端点
        └── cases.py                     # NEW: POST /api/cases/confirm

alembic/                                 # NEW: 数据库迁移
├── alembic.ini
├── env.py
└── versions/

tests/                                   # NEW: 测试目录
├── unit/
├── integration/
└── contract/
```

**Structure Decision**: 沿用现有 `Backend/` 四层结构（Domain/Application/Infrastructure/Web），新增 `Infrastructure/persistence/` 子模块承载 PostgreSQL 实现，`Infrastructure/skill/` 子模块承载 Skill 存根。新增 `alembic/` 用于数据库迁移。文件组织严格遵循宪法目录映射。

## Complexity Tracking

> 无违规需要记录。所有设计均符合宪法原则，无需额外理由。
