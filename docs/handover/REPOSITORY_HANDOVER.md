# UniGuru Repository Handover Record

**Document Version:** 1.0.0  
**Date:** 2026-11-12  
**Task ID:** UG-HO-01 (Priority: P0)  
**Product:** UniGuru  
**Author / Builder:** Vijay Dhawan  
**BHIV Organisation:** BHIV Central Depository (`BHIV-Engineering-Exchange`)  
**Target Repository:** `https://github.com/BHIV-SYSTEM/bhiv-uniguru.git`  
**Handover Branch:** `ug-ho-01-infrastructure-handover`  

---

## 1. Handover Objective & Authority

This document formalizes the repository handover of UniGuru to the BHIV Central Depository. Under the BHIV hypervelocity operating model, this packet preserves all verified functionality, establishes an indisputable baseline of tested code, records duplicate modules and technical debt, and provides an incoming engineer with exact steps to reproduce and extend the verified state without personal knowledge transfer.

---

## 2. Git & Repository Topology

### 2.1 Origin & Organization Details
- **Central Depository Organization:** `BHIV-Engineering-Exchange`
- **Product Repository:** `bhiv-uniguru`
- **Remote Origin URL:** `https://github.com/BHIV-SYSTEM/bhiv-uniguru.git`
- **Remote Default Branch:** `main` (Latest SHA: `ecd9658`)
- **Remote Feature / Handover Branches:**
  - `origin/ug-ho-01-infrastructure-handover` (Current handover branch)
  - `origin/ug-ho-02-knowledge-retrieval` (Adjacent build branch)
  - `origin/feat/indic-squad-marathi-full-training-ready`
  - `origin/integrate-uniguru-fix`
  - `origin/ui-update`

### 2.2 Local Builder Workspace Metadata
- **Physical Directory:** `C:\Users\vijay\OneDrive\Desktop\bhiv-uniguru-main (1)`
- **Active VS Code / IDE Workspace:** `C:\Users\vijay\OneDrive\Desktop\uniguru_error`
- **Source Feature Branch:** `rag-production-upgrade`
- **Base Commit SHA:** `d6bb956` ("checkpoint: baseline before production RAG upgrade")
- **Commit History Preservation:** Linear history preserved from `origin/main` ancestor `c14ef21` through `17d9ddd` and `d6bb956`.

---

## 3. Working-Tree Inventory & Audit

### 3.1 Preserved Working Code (Included in Handover)
The following core enhancements have been verified, tested, and incorporated:
1. `backend/retrieval/retriever.py`: Vocabulary indexing, typo-tolerant fuzzy matching for educational queries, token co-occurrence filtering.
2. `backend/retrieval/unified_rag_engine.py`: Structured provenance formatting (`[Doc] -> Page -> Section`), query-relevant extractive summarization, SHA-256 query fingerprinting in retrieval logs.
3. `backend/router/conversation_router.py`: Robust fallback provider handling with retry loop, exponential backoff, preferential verified RAG routing when requested, prompt sanitization.
4. `backend/service/api.py`: Synchronized multi-route query pipeline, deterministic math engine bypass, safe error class mapping, and security boundary enforcement.
5. `backend/service/auth_service.py`: Standalone SQLite user auth with optional MongoDB sync; removes any external cloud dependency during startup.
6. `backend/tests/`: New test fixtures, conversation router tests, RAG health checks, and unified RAG engine quality suites (`backend/tests/test_unified_rag_engine_quality.py`).
7. `curriculum/` & `backend/data/kosha/`: 37 textbook knowledge records, pedagogical graph manifests, and chapter extraction indices.

### 3.2 Duplicate Modules & Obsolete Paths Audit (CRITICAL)
An audit of the repository tree reveals the following redundant or misplaced artifacts:
1. **Accidental Nested Repository in Git Tree (`bhiv-uniguru-main/`):**
   - *Finding:* In commit `95ea851`, an entire copy of the project was committed inside the subdirectory `bhiv-uniguru-main/`. This contains duplicate `backend/`, `frontend/`, `docs/`, and `tests/` directories.
   - *Status in Handover:* Root files are the authoritative execution source. The nested `bhiv-uniguru-main/` tree is cataloged as P1 technical debt scheduled for cleanup in Task `UG-BL-02`.
2. **Ignored Local Clone (`bhiv-uniguru/`):**
   - *Finding:* A second nested directory `bhiv-uniguru/` exists on the local filesystem. It is properly matched by `.gitignore` and excluded from git tracking.
3. **Large Archive File (`uniguru_ai_source.zip` - 245 MB):**
   - *Finding:* A 245 MB ZIP file exists in the repository root. It is ignored by `.gitignore` (`uniguru_ai_source*`) to prevent repository bloat.
4. **Obsolete Cloud Auth Module:**
   - *Finding:* Previous versions relied on Supabase (`backend/service/supabase_auth.py`). This was completely removed in commit `10184df` in favor of local SQLite auth (`backend/service/auth_service.py`), eliminating external network failure risks during startup.

### 3.3 Secrets & Environment Files Policy
- **Strict Compliance:** No `.env`, `.env.production`, or private credentials have been committed.
- **Example Templates Only:** `.env.example` and `backend/.env.example` provide mock keys (`uniguru_secret_123`) strictly for local developer parity and test suite execution.

---

## 4. Reproducible Setup & Verification Guide

An incoming BHIV engineer can reproduce the full operational baseline using the following deterministic steps:

### Step 1: Environment Initialization
```powershell
# Clone the repository
git clone https://github.com/BHIV-SYSTEM/bhiv-uniguru.git
cd bhiv-uniguru

# Checkout the handover branch
git checkout ug-ho-01-infrastructure-handover

# Create Python 3.11 virtual environment
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install core dependencies
pip install fastapi uvicorn pydantic sentence-transformers faiss-cpu pytest httpx requests
```

### Step 2: Run Automated Test Baseline
```powershell
# Elevate rate limits for batch test execution
$env:UNIGURU_RATE_LIMIT_MAX_REQUESTS = "10000"

# Run tests
python -m pytest tests/ -o addopts="" --tb=short -q
python -m pytest backend/tests/ -o addopts="" --tb=short -q

# Expected outcome: 124 passed in tests/, 343 passed in backend/tests/ (0 failures)
```

### Step 3: Run Application Service
```powershell
$env:PYTHONPATH = "backend"
$env:UNIGURU_HOST = "127.0.0.1"
$env:UNIGURU_PORT = "8000"
$env:UNIGURU_API_AUTH_REQUIRED = "false"
$env:EXTERNAL_API_SECRET_KEY = "uniguru_secret_123"

python -m uvicorn service.api:app --host 127.0.0.1 --port 8000
```

### Step 4: Verify Smoke Endpoints
```bash
# Health check
curl http://127.0.0.1:8000/health

# Educational query
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What is cell division and mitosis?"}'

# Mitra contract query
curl -X POST http://127.0.0.1:8000/new_query \
  -H "Authorization: Bearer uniguru_secret_123" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is karma?", "request_id": "test-01", "intent": "information_retrieval", "required_outputs": ["signals", "final_answer"]}'
```

---

## 5. Rollback & Pre-Handover State

If any unforeseen incompatibility arises, the repository can be restored to the prior baseline:
- **Prior Head Commit:** `d6bb956`
- **Prior Remote Head Commit:** `ecd9658`
- **Prior Release Tag:** `v1.1.0` (commit `10184df`)


### 2.3 Pull Request & Review Access
- **Review PR Link:** [Create / View PR](https://github.com/BHIV-SYSTEM/bhiv-uniguru/pull/new/ug-ho-01-infrastructure-handover)
- **Handover Commit SHA:** `d1c142d`
- **Origin Base Commit SHA:** `ecd9658`

