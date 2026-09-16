# Deployment Summary — UniGuru Runtime

**Environment:** Production / Live Containerized Environment  
**Service Name:** `uniguru-ecosystem-runtime`  
**API Port:** `8001` (Dev) / Mounted under `/v2` in Main Service  
**Runtime Owner:** Isha Singh  

---

## 1. Startup & Component Loading

```text
============================================================
  BENCHMARK 1: Module Startup Time
============================================================
  kosha.kosha_loader                            OK  (458.784 ms)
  kosha.kosha_retriever                         OK  (0.007 ms)
  kosha.deterministic_pipeline                  OK  (46.671 ms)
  retrieval.ontology_retriever                  OK  (0.005 ms)
  ontology.entity_resolver                      OK  (0.003 ms)
  governance.source_governance                  OK  (0.003 ms)

  Total import time: 505.47 ms
```

---

## 2. API Endpoints Matrix

| Endpoint | Method | Purpose | Health Status |
|---|---|---|---|
| `/health` | GET | Ecosystem runtime capabilities & service health | `200 OK` |
| `/ready` | GET | MasterDB & proof directory readiness | `200 OK` |
| `/metrics` | GET | Prometheus operational metrics | `200 OK` |
| `/v2/runtime/sanskrit/decode` | POST | Native Sanskrit Knowledge Decoder | `200 OK` |
| `/v2/runtime/sanskrit/graph/traverse` | POST | Multi-hop Knowledge Graph traversal | `200 OK` |
| `/v2/convergence/authority_map` | GET | Knowledge source authority hierarchy | `200 OK` |
| `/v2/convergence/validate_evidence` | POST | Claim-to-evidence validation engine | `200 OK` |

---

## 3. Configuration & Environment Variables

- `UNIGURU_SANSKRIT_API_URL`: `http://localhost:8001`
- `UNIGURU_ENGINE_URL`: Deployed API base URL
- `INSIGHTFLOW_TOKEN`: Operational observability token
- `PROOFS_DIRECTORY`: `review_packets/proof_logs/`
