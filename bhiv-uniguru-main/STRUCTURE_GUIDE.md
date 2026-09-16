# UniGuru Repository Structure Guide

Quick reference for navigating the UniGuru codebase.

## Top-Level Directories

| Directory | Purpose | Key Files |
|-----------|---------|-----------|
| `backend/` | Python Intelligence Engine | `main.py`, `requirements.txt` |
| `frontend/` | React Chat UI | `package.json`, `src/` |
| `node-backend/` | Node.js Middleware (optional) | `src/server.js` |
| `deploy/` | Docker, NGINX, TLS | `nginx/`, `certbot/` |
| `docs/` | All Documentation | See below |
| `scripts/` | Utility Scripts | `ingest_kb.py`, `run_tests.sh` |
| `run/` | Startup Scripts | `run_backend.sh`, `run_node.sh` |

## Backend Structure (`backend/`)

| Module | Purpose | Key Files |
|--------|---------|-----------|
| `service/` | FastAPI API Layer | `api.py`, `live_service.py`, `query_classifier.py` |
| `router/` | Conversation Routing | `conversation_router.py` |
| `core/` | Rule Engine | `engine.py`, `rules/` |
| `governance/` | Safety Rules | `ambiguity.py`, `authority.py`, `delegation.py`, `emotional.py` |
| `enforcement/` | Response Sealing | `enforcement.py`, `seal.py`, `safety.py` |
| `retrieval/` | KB + Web Retrieval | `retriever.py`, `web_retriever.py`, `kb_engine.py` |
| `reasoning/` | Ontology Reasoning | `concept_resolver.py`, `graph_reasoner.py` |
| `ontology/` | Concept Graph | `schema.py`, `graph.py`, `registry.py`, `snapshots/` |
| `verifier/` | Source Verification | `source_verifier.py` |
| `truth/` | Truth Validation | `truth_validator.py` |
| `stt/` | Speech-to-Text | `stt_engine.py` |
| `bridge/` | Legacy System Bridge | `server.py`, `auth.py` |
| `integrations/` | External Adapters | `bucket_telemetry.py`, `gurukul/` |
| `loaders/` | KB Ingestion | `file_parser.py`, `ingestor.py` |
| `knowledge/` | Knowledge Bases | `quantum/`, `jain/`, `swaminarayan/`, `gurukul/` |

## Knowledge Bases (`backend/knowledge/`)

| KB | Files | Description |
|----|-------|-------------|
| `quantum/` | 19 | Quantum computing, algorithms, hardware |
| `jain/` | 10 | Jain philosophy primary texts |
| `swaminarayan/` | 10 | Swaminarayan philosophy primary texts |
| `gurukul/` | 6 | Gurukul curriculum (math, logic, Sanskrit, sciences) |
| `index/` | 2 | Generated indices (`master_index.json`, `runtime_manifest.json`) |

## Documentation Structure (`docs/`)

| Directory | Purpose | Key Files |
|-----------|---------|-----------|
| `architecture/` | System Design | `SYSTEM_FLOW.md`, `RULE_ENGINE.md`, `ONTOLOGY.md`, `ROUTER.md` |
| `api/` | API Specifications | `API_SPEC.md`, `PUBLIC_API_USAGE.md` |
| `knowledge-base/` | KB Documentation | `KB_INDEX.md`, `SOURCE_INDEX.md` |
| `deployment/` | Deployment Guides | `PRODUCTION_RUNBOOK.md`, `DEPLOYMENT_CHECKLIST.md` |
| `handover/` | Onboarding | `SETUP_GUIDE.md`, `FAILURE_HANDLING.md`, `FAQ.md` |
| `reports/` | Task Reports | 40+ completion reports |

## Frontend Structure (`frontend/src/`)

| Directory | Purpose | Key Files |
|-----------|---------|-----------|
| `components/` | UI Components | `ChatWidget.tsx`, `MessageBubble.tsx`, `VerificationBadge.tsx`, `VoiceInput.tsx` |
| `services/` | API Client | `uniguru-api.ts` |
| `hooks/` | React Hooks | `useChat.ts`, `useVoice.ts` |
| `types/` | TypeScript Types | `uniguru.ts` |

## Tests (`backend/tests/`)

All tests are in one location:

- `test_engine.py` - Rule engine tests
- `test_governance.py` - Governance rules
- `test_ontology.py` - Ontology integrity
- `test_retrieval.py` - KB retrieval (if exists)
- `test_router.py` - Conversation router
- `test_service.py` - API endpoints
- `test_stt.py` - Speech-to-text
- `test_bridge.py` - Bridge server
- Plus 11 more test files

## Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `ingest_kb.py` | Rebuild KB indices |
| `run_tests.sh` | Run all tests |
| `run_phase8_validation.py` | End-to-end validation |
| `run_demo_safety_proof.py` | Safety proof tests |
| `run_kb_coverage_snapshot.py` | KB coverage analysis |
| `start.sh` | Start backend + bridge |

## Common Tasks

### Run Backend
```bash
bash run/run_backend.sh
```

### Run Frontend
```bash
cd frontend && npm run dev
```

### Run Tests
```bash
cd backend && pytest tests/ -v
```

### Ingest KB
```bash
python scripts/ingest_kb.py
```

### Check Ontology
```bash
cd backend && python -m uniguru.ontology.replay_test
```

### Validate System
```bash
python scripts/run_phase8_validation.py
```

## Key Files

| File | Purpose |
|------|---------|
| `README.md` | Main project documentation |
| `.gitignore` | Git ignore patterns |
| `docker-compose.yml` | Docker orchestration |
| `Dockerfile` | Backend container |
| `pytest.ini` | Pytest configuration |
| `.env.example` | Environment template |

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/ask` | POST | Main query endpoint |
| `/voice/query` | POST | Speech-to-text query |
| `/health` | GET | Health check |
| `/metrics` | GET | System metrics |

## Environment Variables

Key variables (see `.env.example`):

- `UNIGURU_HOST` - Backend host
- `UNIGURU_PORT` - Backend port
- `UNIGURU_API_TOKEN` - API authentication token
- `UNIGURU_ALLOWED_CALLERS` - Allowed caller IDs
- `UNIGURU_LLM_URL` - LLM endpoint (optional)

## Quick Navigation

**Need to understand the system?**
→ Start with `docs/HANDOVER.md`

**Need to understand the architecture?**
→ Read `docs/architecture/SYSTEM_FLOW.md`

**Need to understand the API?**
→ Read `docs/api/API_SPEC.md`

**Need to deploy?**
→ Follow `docs/deployment/PRODUCTION_RUNBOOK.md`

**Need to add knowledge?**
→ Add files to `backend/knowledge/[domain]/` then run `scripts/ingest_kb.py`

**Need to modify rules?**
→ Edit files in `backend/uniguru/core/rules/`

**Need to modify routing?**
→ Edit `backend/uniguru/router/conversation_router.py`

**Need to modify UI?**
→ Edit files in `frontend/src/components/`

## File Naming Conventions

- Python modules: `snake_case.py`
- TypeScript/React: `PascalCase.tsx` for components, `camelCase.ts` for utilities
- Documentation: `UPPER_CASE.md` for major docs, `Title_Case.md` for guides
- Tests: `test_*.py` (pytest convention)
- Scripts: `run_*.py` or `*.sh`

## Import Patterns

**Correct:**
```python
from retrieval.retriever import AdvancedRetriever
from retrieval.kb_engine import retrieve
from retrieval.web_retriever import web_retrieve
```

**Incorrect (old paths):**
```python
from uniguru.retrieval.retriever import ...  # OLD - don't use
from uniguru.retriever.engine import ...      # OLD - don't use
from uniguru.Quantum_KB import ...            # OLD - don't use
```

## KB Paths

**Correct:**
- `backend/knowledge/quantum/`
- `backend/knowledge/jain/`
- `backend/knowledge/swaminarayan/`
- `backend/knowledge/gurukul/`

**Incorrect (old paths):**
- `backend/uniguru/knowledge/quantum/` - OLD
- `uniguru/Quantum_KB/` - OLD
- `knowledge/index/` (at root) - OLD

## Status: Current Structure

✅ Clean and organized  
✅ Follows TASK14 specification  
✅ No redundant folders  
✅ No dead code  
✅ Single source of truth for all components  
✅ Proper separation of concerns  

Last updated: March 23, 2026
