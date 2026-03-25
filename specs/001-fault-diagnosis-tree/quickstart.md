# Quickstart: 智能故障诊断与故障树生成系统

**Feature**: 001-fault-diagnosis-tree

---

## Prerequisites

- Python 3.11+
- PostgreSQL 14+ (running locally or via Docker)
- uv (package manager)

## Setup

```bash
# 1. Clone and activate
cd RAG
uv venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/Mac

# 2. Install dependencies
uv pip install -r requirements.txt

# 3. Configure environment variables
# Edit .env file:
#   DEEPSEEK_API_KEY=sk-your-key
#   DATABASE_URL=postgresql://user:password@localhost:5432/rag_diagnosis

# 4. Initialize PostgreSQL database (Alembic migrations)
alembic upgrade head

# 5. Start the server
python main.py
```

Server starts at `http://localhost:8080`

---

## End-to-End Smoke Test

### Step 1: Upload a document to the knowledge base

```bash
curl -X POST http://localhost:8080/api/documents/upload \
  -F "file=@maintenance_manual.pdf"
```

Expected: `{"status": "success", "total_chunks": 45, "persisted_chunks": 38, ...}`

### Step 2: Create a diagnosis session

```bash
curl -X POST http://localhost:8080/api/diagnosis/sessions \
  -H "Content-Type: application/json" \
  -d '{"initial_message": "设备启动后温度异常升高"}'
```

Expected: 201 with `session_id` and AI reply asking clarifying questions.

### Step 3: Continue the diagnosis dialogue

```bash
curl -X POST http://localhost:8080/api/diagnosis/sessions/{session_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"message": "是3号电机，温度到了85度，从昨天开始"}'
```

Expected: AI reply with knowledge-based guidance. Repeat 3-5 rounds until `diagnosis_sufficient: true`.

### Step 4: Generate a fault tree

```bash
curl -X POST http://localhost:8080/api/fault-trees/generate \
  -H "Content-Type: application/json" \
  -d '{"session_id": "{session_id}"}'
```

Expected: 201 with fault tree JSON in `draft` status.

### Step 5: Review and modify the fault tree (optional)

```bash
curl -X PUT http://localhost:8080/api/fault-trees/{fault_tree_id} \
  -H "Content-Type: application/json" \
  -d '{"name": "修订版故障树", "root": {...}}'
```

### Step 6: Confirm and archive as a case

```bash
curl -X POST http://localhost:8080/api/cases/confirm \
  -H "Content-Type: application/json" \
  -d '{"fault_tree_id": "{fault_tree_id}"}'
```

Expected: `{"status": "confirmed", "text_file_generated": true, "standardization": {"status": "success"}}` or standardization failure with data safely persisted.

---

## Verification Checklist

- [ ] Document upload returns chunk statistics with deduplication info
- [ ] Session creation returns an AI-guided response
- [ ] Multi-turn dialogue retrieves relevant knowledge base content
- [ ] System suggests fault tree generation when info is sufficient
- [ ] Fault tree JSON follows the defined schema (node types, gate types)
- [ ] Fault tree modification validates structural integrity
- [ ] Case confirmation persists to PostgreSQL
- [ ] Standardization failure does not lose case data
