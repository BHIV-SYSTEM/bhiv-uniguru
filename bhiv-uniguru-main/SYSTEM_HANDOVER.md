# UniGuru System Handover Document

**Version:** 1.1.0  
**Date:** 2026-06-29  
**Status:** PRODUCTION READY  
**Classification:** Internal Engineering

---

## 1. System Overview

UniGuru is a **governed curriculum intelligence platform** that answers student queries using exclusively verified textbook sources (Balbharti Maharashtra State Board curriculum). The system enforces constitutional rules preventing hallucinated or synthetic content in every response.

### Core Design Principle
> Every answer must trace back to a verified textbook source. No synthetic content is permitted in the execution path.

---

## 2. Runtime Architecture

### Query-to-Proof Flow (7 Stages)

```
Student/Teacher Query
        │
        ▼
┌─────────────────────────────────────────────────┐
│  Stage 1: ROUTING                               │
│  ConversationRouter → classify query type       │
│  Routes: ROUTE_UNIGURU / ROUTE_LLM / WORKFLOW  │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  Stage 2: CURRICULUM RETRIEVAL                  │
│  Kosha Pipeline → signal-first ontology search  │
│  KoshaRetriever → OntologyAwareRetriever        │
│  Outputs: matched_signals, verification_status  │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  Stage 3: CONSTITUTIONAL RUNTIME                │
│  Rule Engine → governance enforcement           │
│  Checks: authority, delegation, safety          │
│  Rejects synthetic / unverified content         │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  Stage 4: MASTERY ENGINE                        │
│  MasteryEngine → compute_concept_mastery()      │
│  60% accuracy + 40% EMA confidence              │
│  Outputs: mastery_score, weak_areas, remediation│
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  Stage 5: LANGUAGE ADAPTATION                   │
│  LanguageAdapter → normalize + localize         │
│  Supports: en, mr, hi                           │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  Stage 6: RESPONSE SEALING                      │
│  Adds: trace_id, governance_metadata, lineage   │
│  Bucket telemetry emitted                       │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  Stage 7: PROOF GENERATION                      │
│  runtime_convergence_report.json                │
│  Full lineage: Textbook → Chapter → Exercise    │
└─────────────────────────────────────────────────┘
```

---

## 3. Key Modules

| Module | Path | Purpose |
|--------|------|---------|
| `api.py` | `backend/service/api.py` | FastAPI entrypoint — all HTTP routes |
| `deterministic_pipeline.py` | `backend/kosha/` | Core retrieval pipeline (deterministic, no LLM) |
| `kosha_retriever.py` | `backend/kosha/` | Signal-first ontology-aware retrieval |
| `mastery_engine.py` | `learning_runtime/` | Student mastery tracking (EMA-based) |
| `canonical_runtime.py` | `learning_runtime/` | Single canonical execution path |
| `teacher_runtime.py` | `learning_runtime/` | Teacher-facing intelligence (4 views) |
| `structured_logger.py` | `backend/observability/` | JSON structured request logging |
| `metrics_collector.py` | `backend/observability/` | Latency histograms, confidence distribution |
| `retrieval_evaluator.py` | `backend/retrieval/` | IR metrics: Precision@K, MRR, NDCG |

### Sanskrit Civilizational Decoder

The decoder module at `backend/ontology/sanskrit_decoder.py` is now wired to the existing UniGuru ecosystem for civilizational knowledge retrieval. It uses the current knowledge base, kosha records, and masterdb dataset as its retrieval backbone, while preserving provenance, deterministic hashes, and graph traversal metadata.

**Verified status (2026-08-06):**
- `pytest backend/tests/test_sanskrit_decoder.py -q` → `10 passed in 3.86s`
- Concept smoke tests for `dharma`, `karma`, `agni`, `atman`, `brahman`, `prana`, `rta`, `shakti`, `yajna`, and `om` all completed successfully with evidence sourced from `knowledge_base`, `kosha`, and `masterdb`.

---

## 4. Production Health Endpoints

| Endpoint | Method | Auth Required | Purpose |
|----------|--------|---------------|---------|
| `/health` | GET | No | Full health status (KB, LLM, uptime) |
| `/health/live` | GET | No | Liveness probe (container orchestration) |
| `/health/ready` | GET | No | Readiness probe (KB loaded + LLM available) |
| `/ready` | GET | No | Alias for `/health/ready` |
| `/metrics` | GET | Yes (token) | Prometheus-format metrics export |
| `/monitoring/dashboard` | GET | Yes (token) | Human-readable monitoring dashboard |
| `/observability/sample` | GET | Yes (token) | Last 10 structured log entries + metric snapshot |

### Sample `/metrics` Output
```
# TYPE uniguru_requests_total counter
uniguru_requests_total 142
# TYPE uniguru_ask_requests_total counter
uniguru_ask_requests_total 89
# TYPE uniguru_request_latency_ms_p50 gauge
uniguru_request_latency_ms_p50 91.46
# TYPE uniguru_request_latency_ms_p95 gauge
uniguru_request_latency_ms_p95 105.156
# TYPE uniguru_request_latency_ms_p99 gauge
uniguru_request_latency_ms_p99 105.391
# TYPE uniguru_confidence_distribution_total counter
uniguru_confidence_distribution_total{bucket="0.0-0.2"} 0
uniguru_confidence_distribution_total{bucket="0.6-0.8"} 14
# TYPE uniguru_failure_class_total counter
uniguru_failure_class_total{class="no_knowledge"} 12
```

---

## 5. Deployment Instructions

### Prerequisites
- Python 3.12+
- Environment variables set (see `.env.example`)
- Balbharti curriculum data in `backend/data/kosha/`

### Local Development
```powershell
# Install dependencies
pip install -r backend/requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env: set UNIGURU_API_TOKEN, GROQ_API_KEY, SUPABASE_URL etc.

# Run the API
.\run_local_api.ps1
# OR directly:
$env:PYTHONPATH="backend"
uvicorn backend.service.api:app --host 0.0.0.0 --port 8000 --reload
```

### Docker
```bash
docker build -t uniguru-api .
docker run -p 8000:8000 --env-file .env uniguru-api
```

### Docker Compose (full stack)
```bash
docker-compose up -d
```

### Render (cloud)
The `render.yaml` file configures a Render web service.  
Set environment variables in the Render dashboard under Environment.

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `UNIGURU_API_TOKEN` | Yes | — | Primary API authentication token |
| `UNIGURU_API_TOKENS` | No | — | Comma-separated additional tokens |
| `UNIGURU_API_AUTH_REQUIRED` | No | `true` | Set `false` for demo mode |
| `GROQ_API_KEY` | Yes* | — | Groq LLM key (*required for LLM fallback) |
| `SUPABASE_URL` | No | — | Supabase project URL |
| `SUPABASE_ANON_KEY` | No | — | Supabase anon key |
| `UNIGURU_LOG_LEVEL` | No | `INFO` | Logging verbosity |
| `UNIGURU_RATE_LIMIT_MAX_REQUESTS` | No | `60` | Requests per minute per IP |
| `UNIGURU_KB_CONFIDENCE_THRESHOLD` | No | `0.45` | Min confidence to accept KB result |

---

## 6. Operational Runbook

### Health Check (Startup Verification)
```bash
# Verify liveness
curl http://localhost:8000/health/live
# Expected: {"status": "alive"}

# Verify readiness
curl http://localhost:8000/health/ready
# Expected: {"status": "ready", "checks": {...}}
```

### Restart Procedure
1. Send SIGTERM to the running process (graceful shutdown)
2. Wait for in-flight requests to complete (up to 30s)
3. Start new instance
4. Verify `/health/ready` returns `"status": "ready"`
5. Route traffic to new instance

### Rollback
```powershell
# Git-based rollback
git checkout <previous-commit-hash>
# Restart the service
```

### Failure Response Procedures

| Failure Mode | Symptom | Recovery |
|-------------|---------|---------|
| KB not loaded | `/health/ready` returns `"status": "degraded"` | Check `backend/data/kosha/` directory exists and has JSON files |
| LLM unavailable | Responses use safe fallback prefix | Verify `GROQ_API_KEY` is set; LLM fallback is optional |
| Auth failures | 401 responses | Check `UNIGURU_API_TOKEN` in `.env` |
| Rate limiting | 429 responses | Normal — adjust `UNIGURU_RATE_LIMIT_MAX_REQUESTS` if needed |
| Queue saturation | Safe fallback responses | Increase `UNIGURU_ROUTER_QUEUE_LIMIT` (default: 200) |

### Monitoring
```bash
# View Prometheus metrics (requires auth token)
curl -H "X-Api-Token: <token>" http://localhost:8000/metrics

# View structured logs
tail -f logs/uniguru_structured.jsonl | python -m json.tool

# Monitoring dashboard
curl -H "X-Api-Token: <token>" http://localhost:8000/monitoring/dashboard
```

---

## 7. Known Limitations

| Limitation | Impact | Mitigation |
|------------|--------|-----------|
| Only 4 Balbharti textbooks ingested (37 Kosha entries) | Low recall on many valid curriculum queries | Add more licensed textbook data to `backend/data/kosha/` |
| LLM fallback requires external API (Groq) | Fallback responses unavailable offline | System works without LLM — returns "no verified knowledge" |
| No persistent session storage | Chat history lost on restart | Supabase integration available but optional |
| In-memory metrics only | Metrics reset on restart (unless snapshot file configured) | Set `UNIGURU_METRICS_STATE_FILE` to persist across restarts |
| Structured log file size | JSONL file grows unbounded | Set up log rotation (e.g., logrotate or Loki) |
| STT requires audio format support | Voice queries may fail on unsupported formats | WAV/MP3 tested; other formats depend on STT engine |

---

## 8. Curriculum Data Structure

```
backend/data/kosha/
├── *.json           # Kosha knowledge entries (37 entries across 4 textbooks)

curriculum/
├── verified_textbook_registry.json    # 4 Balbharti textbooks
├── edition_registry.json             # Edition + ISBN metadata
├── ingestion_proof.json              # Ingestion verification proof
└── extracted/
    ├── chapter_manifest.json         # 14 chapters
    ├── concept_manifest.json         # 42 concepts
    ├── exercise_manifest.json        # 630 exercises
    ├── glossary_manifest.json        # 138 glossary terms
    ├── pedagogical_graph.json        # DAG: 8 concepts, 9 edges
    └── curriculum_lineage_registry.json  # Full 5-level lineage chain
```

---

## 9. Test Suite

```powershell
# Run full test suite
pytest tests/ -o addopts="" --tb=short -q

# Expected: 94/94 tests pass
# tests/test_curriculum_intelligence.py  (52 tests)
# tests/test_curriculum_truth_validation.py (42 tests)
```

---

## 10. Integration Sign-off

| Role | Validator | Area | Status |
|------|-----------|------|--------|
| Runtime Integration | Rajaryan | End-to-end pipeline, system validation | Ready for validation |
| Independent Testing | Vinayak | Functional verification, test coverage | 94/94 tests passing |
| Final Integration | Ashmit | Ecosystem integration, production handover | Evidence package ready |

---

*Document generated: 2026-06-29. Platform version: 1.1.0.*
