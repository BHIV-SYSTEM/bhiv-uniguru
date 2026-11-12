# UniGuru Infrastructure Baseline

**Document Version:** 1.0.0  
**Date:** 2026-11-12  
**Task ID:** UG-HO-01 (Priority: P0)  
**Product:** UniGuru (BHIV Central Depository)  
**Owner / Primary Engineer:** Vijay Dhawan  
**System Classification:** Governed Curriculum Intelligence Platform  
**Target Environment:** Local Parity / Python 3.11 / Render Production  

---

## 1. Executive Summary & System Overview

UniGuru is the governed curriculum intelligence platform for the BHIV Enterprise Operating System Common Core. Its primary mandate is to provide authoritative, textbook-grounded answers to educational and cultural queries (specifically aligned with Balbharati Maharashtra State Board curriculum and Indian pedagogical sources) while enforcing strict constitutional governance against synthetic hallucination.

### Non-Negotiable Operational Principles
1. **Source Grounding Before Synthesis:** Every curriculum claim must resolve to an authoritative, verified textbook chapter, page, or Kosha signal.
2. **Zero Unverified Hallucination:** If no verified knowledge is available and strict verification is required, the system explicitly abstains with `NO_VERIFIED_KNOWLEDGE`.
3. **Resilient Local Runtime:** System operation does not depend on cloud databases or external auth providers. Core persistence is local SQLite with graceful MongoDB synchronization.

---

## 2. Repository & Runtime Topology

```
bhiv-uniguru/
├── backend/
│   ├── capabilities/           # Specialized capability engines (MathEngine, CodeEngine)
│   ├── data/
│   │   ├── kosha/              # 37 verified Kosha textbook knowledge entries (JSON)
│   │   └── retrieval_logs/     # Ephemeral retrieval audit logs
│   ├── knowledge/              # 114 curated curriculum markdown knowledge documents
│   ├── kosha/                  # Deterministic signal extraction, ontology resolution & synthesis
│   ├── retrieval/              # Advanced retriever & UnifiedRAGEngine (FAISS + Dense embeddings)
│   ├── router/                 # ConversationRouter (Query routing: Kosha vs RAG vs Capability vs LLM)
│   ├── service/                # FastAPI live reasoning API (api.py), auth (auth_service.py), orchestrator
│   └── tests/                  # 343 comprehensive backend unit, contract & integration tests
├── curriculum/                 # Textbook registries, chapter/concept manifests & pedagogical graphs
├── deploy/                     # Deployment configurations and release assets
├── docs/                       # Architectural documentation, handover packets & manuals
├── frontend/                   # React 18 + TypeScript + Vite UI application
├── logs/                       # Local persistent state (chats.sqlite3, users.sqlite3, uniguru_structured.jsonl)
├── review_packets/             # Ecosystem proof logs, contract traces, and review packets
├── scripts/                    # Evaluation, benchmark & ingestion utilities
└── tests/                      # 124 end-to-end curriculum intelligence & truth validation tests
```

---

## 3. Runtime Entry Points & Invocation

### 3.1 Backend Application Service
- **Primary Entry Module:** `backend/service/api.py`
- **ASGI App Instance:** `service.api:app`
- **Application Framework:** FastAPI 0.141.1 / Starlette / Uvicorn 0.52.4
- **Startup Command (Production & Local):**
  ```powershell
  $env:PYTHONPATH = "backend"
  uvicorn service.api:app --host 0.0.0.0 --port 8000 --workers 1
  ```

### 3.2 Frontend Web Application
- **Directory:** `frontend/`
- **Framework:** React 18.3.1, TypeScript, Tailwind CSS, Vite 5.4.21
- **Build Command:** `npm run build` (`tsc -b && vite build`)
- **Development Server:** `npm run dev` (Default port: 5173, proxies to backend `http://localhost:8000`)
- **Configured Base URL:** Controlled via `VITE_API_BASE_URL` (`.env.development` -> `http://127.0.0.1:8000`, `.env.production` -> `https://complete-uniguru.onrender.com`)

---

## 4. Environment Configuration Specification

| Variable Name | Default Value | Description / Purpose |
|---|---|---|
| `PYTHONPATH` | `backend` | Ensures absolute module resolution from `backend/` root |
| `UNIGURU_HOST` | `0.0.0.0` | Socket binding address |
| `UNIGURU_PORT` | `8000` | Socket listening port |
| `UNIGURU_ENVIRONMENT` | `development` | Environment tier (`development`, `test`, `production`) |
| `UNIGURU_API_AUTH_REQUIRED` | `false` | When `true`, enforces Bearer token authentication on `/ask` and `/api/chat` |
| `EXTERNAL_API_SECRET_KEY` | `uniguru_secret_123` | Shared secret key for internal service-to-service calls (`/new_query`) |
| `UNIGURU_ALLOWED_CALLERS` | `*` | Comma-delimited list of permitted caller IDs (e.g. `mitra,tantra,system`) |
| `UNIGURU_RATE_LIMIT_MAX_REQUESTS` | `60` (Elevate to `10000` in tests) | Maximum requests per sliding 60-second window per client IP |
| `UNIGURU_RATE_LIMIT_WINDOW_SECONDS` | `60` | Duration of rate-limiting time window |
| `GROQ_API_KEY` | None (Optional) | API key for external LLM fallback (Groq / Llama 3) |
| `MONGODB_URI` | None (Optional) | Connection URI for persistent cloud user database |
| `UNIGURU_USER_DB_PATH` | `logs/users.sqlite3` | Local persistent SQLite user auth database |
| `UNIGURU_METRICS_STATE_FILE` | None (Optional) | Snapshot file to persist in-memory metrics across restarts |

---

## 5. API Request & Response Contracts

### 5.1 Health & Liveness Checks
- `GET /health`  
  **Status Code:** `200 OK`  
  **Contract:**
  ```json
  {
    "status": "ok",
    "service": "uniguru-live-reasoning",
    "version": "1.1.0",
    "uptime_seconds": 12.45,
    "checks": {
      "ontology_registry": "ok",
      "reasoning_service": "ok",
      "router_active": true,
      "kb_loaded": true,
      "llm_available": false
    },
    "auth": {
      "required": false,
      "mode": "disabled",
      "token_count": 0
    },
    "router": { "allow_unverified_fallback": true },
    "kb": { "loaded": true, "markdown_files": 114 }
  }
  ```
- `GET /health/ready`  
  **Status Code:** `200 OK`  
  **Status Value:** `"ready"` (if all systems including LLM online) or `"degraded"` (if local KB is online but external LLM is offline).

### 5.2 Student / Educational Query (`POST /ask`)
- **Headers:** `Content-Type: application/json`, optional `X-Caller-Name: student-portal`
- **Request:**
  ```json
  {
    "query": "What is cell division and mitosis?",
    "session_id": "optional-uuid",
    "context": { "domain": "Science", "grade": "10" }
  }
  ```
- **Response (`200 OK`):**
  ```json
  {
    "answer": "**Cell Division And Mitosis**:\n\nMitosis is the process of nuclear division...",
    "verification_status": "VERIFIED",
    "confidence": 0.95,
    "decision": "answer",
    "reasoning_trace": [
      { "step": "router", "route": "DETERMINISTIC_KOSHA" },
      { "step": "evidence_selection", "signals_found": 3 }
    ],
    "routing": { "category": "SCIENCE", "selected_engine": "kosha" },
    "trace_id": "2aeab861-8a4a-4e5f-8f72-f57e504a5909"
  }
  ```

### 5.3 BHIV / Mitra Ecosystem Contract (`POST /new_query`)
- **Headers:** `Authorization: Bearer <EXTERNAL_API_SECRET_KEY>`, `Content-Type: application/json`
- **Request:**
  ```json
  {
    "query": "What is karma?",
    "request_id": "mitra-req-001",
    "intent": "information_retrieval",
    "context": { "caller": "mitra", "user_id": "student-001" },
    "required_outputs": ["signals", "final_answer"]
  }
  ```
- **Response (`200 OK`):**
  ```json
  {
    "answer": "**karma**:\n\n**Evidence-based summary:** Karma is the universal principle...",
    "verification_status": "VERIFIED",
    "confidence": 0.92,
    "trace_id": "mitra-req-001",
    "matched_signals": [
      {
        "signal_id": "sig_mitra-req-001_0",
        "confidence": 0.95,
        "source": "jain_karma_doctrine.md",
        "domain": "philosophy"
      }
    ],
    "output_contract": { "schema": "UNIGURU_HYBRID_RAG_CONTRACT_V1", "status": "COMPLIANT" },
    "downstream_execution": { "caller": "mitra", "ready_for_dispatch": true }
  }
  ```

---

## 6. Routing & Orchestration Architecture

```
User / Ecosystem Query
       │
       ▼
UniversalQueryRouter
  ├── Category: MATHEMATICS ─────────► MathEngine (Deterministic solver)
  ├── Category: CODE ────────────────► CodeEngine (Algorithmic runner)
  ├── Strict / Balbharati Query ─────► KoshaDeterministicPipeline (Signal-first ontology)
  │                                           │ (If verified signal found)
  │                                           ▼
  │                                    AnswerSynthesizer (Strict provenance citations)
  │
  ├── Knowledge / Context Query ─────► UnifiedRAGEngine (FAISS dense vector + BM25)
  │                                           │
  │                                           ▼
  │                                    Grounded Extractive Summary + Provenance
  │
  └── Conversational / Creative ─────► ConversationRouter LLM Provider (Groq / Retry loop)
                                              │ (If provider unavailable)
                                              ▼
                                       Controlled Abstention ("NO_VERIFIED_KNOWLEDGE")
```

---

## 7. Security, Auth & Persistence Boundaries

1. **Authentication:**
   - Standalone native SQLite storage (`logs/users.sqlite3`).
   - PBKDF2 password hashing with secure salt.
   - Session tokens generated via cryptographically secure random bytes (`secrets.token_hex(32)`).
   - Seamless background synchronization to MongoDB if `MONGODB_URI` is supplied; zero failure if MongoDB is unreachable.
2. **Permission Boundary:**
   - Ecosystem endpoint (`/new_query`) strictly requires `EXTERNAL_API_SECRET_KEY` via Bearer token, returning `401 Unauthorized` on missing or invalid tokens.
   - Internal student endpoints (`/ask`) default to open for local parity but enforce authentication when `UNIGURU_API_AUTH_REQUIRED=true`.
3. **Abuse Mitigation:**
   - Sliding-window in-memory rate limiter per IP (`UNIGURU_RATE_LIMIT_MAX_REQUESTS` requests per 60s).
   - Returns structured `429 Too Many Requests` with `X-RateLimit-Limit` and `X-RateLimit-Window-Seconds` response headers.
4. **State Persistence:**
   - `logs/users.sqlite3`: Persistent user accounts.
   - `logs/chats.sqlite3`: Session chat histories, query-response transcripts.
   - `logs/uniguru_structured.jsonl`: Structured JSON log events.

---

## 8. Verified Test Baseline

The test infrastructure is composed of two primary suites:
1. `tests/`: End-to-end integration, truth validation, and curriculum intelligence.
   - Total Tests: **124**
   - Result: **124 Passed, 0 Failed** (100% pass rate)
2. `backend/tests/`: Unit tests, router validation, RAG engine quality, and security boundaries.
   - Total Tests: **344**
   - Result: **343 Passed, 1 Skipped, 0 Failed** (100% pass rate)
3. Total Verified Test Suite: **467 Tests Passing Deterministically**.
