# UniGuru Operational Runbook

**Version:** 1.1.0  
**Audience:** Site Reliability Engineers, DevOps, On-call Engineers  
**Scope:** Day-2 operations for the UniGuru Live Reasoning Service

---

## 1. Service Overview

UniGuru is a FastAPI service running on Python 3.12+ with Uvicorn.  
Default port: **8000**. All endpoints documented at `/docs`.

---

## 2. Health Verification (First Thing After Deployment)

```bash
# Step 1: Liveness
curl http://host:8000/health/live
# Expected: {"status":"alive"}

# Step 2: Readiness
curl http://host:8000/health/ready
# Expected: {"status":"ready","checks":{"kb_loaded":true,"llm_status":"available",...}}

# Step 3: Full health
curl http://host:8000/health
# Expected: {"status":"ok","uptime_seconds":N,"checks":{...}}
```

If `/health/ready` returns `"status":"degraded"`:
- Check KB: `ls backend/data/kosha/*.json` — must exist
- Check LLM: Verify `GROQ_API_KEY` in env

---

## 3. Monitoring

### Prometheus Scrape
```bash
curl -H "X-Api-Token: $TOKEN" http://host:8000/metrics
```

Key metrics:
```
uniguru_requests_total              # All HTTP requests
uniguru_ask_requests_total          # Reasoning queries
uniguru_verification_success_rate   # % VERIFIED + PARTIAL responses
uniguru_request_latency_ms_p50      # Median latency
uniguru_request_latency_ms_p95      # 95th percentile latency
uniguru_confidence_distribution_total{bucket="0.6-0.8"}  # Confidence histogram
uniguru_failure_class_total{class="no_knowledge"}         # Rejection counts
```

### Structured Logs
```bash
# Real-time structured log stream
tail -f logs/uniguru_structured.jsonl | python -m json.tool

# Example log entry:
# {"timestamp":"2026-06-29T08:18:50Z","service":"uniguru-live-reasoning",
#  "level":"INFO","request_id":"abc123","method":"POST","route":"/ask",
#  "status_code":200,"latency_ms":103.4}
```

### Dashboard
```bash
curl -H "X-Api-Token: $TOKEN" http://host:8000/monitoring/dashboard
```

---

## 4. Restart Procedure

### Graceful Restart (Recommended)
```bash
# 1. Send graceful stop signal
kill -SIGTERM $(pgrep -f "uvicorn backend.service.api")

# 2. Wait for drain (max 30 seconds)
sleep 5

# 3. Start new instance
uvicorn backend.service.api:app --host 0.0.0.0 --port 8000

# 4. Verify health
curl http://localhost:8000/health/live
```

### Docker Restart
```bash
docker restart uniguru-api
# Verify
docker logs uniguru-api --tail 20
curl http://localhost:8000/health/ready
```

---

## 5. Rollback Procedure

```bash
# Git-based rollback
git log --oneline -5      # Find previous stable commit
git checkout <commit-hash>
# Restart service (see Section 4)
```

---

## 6. Scaling

The service is stateless (in-memory metrics only by default).  
Scale horizontally by running multiple instances behind a load balancer.

```bash
# Example: 3 instances on ports 8000, 8001, 8002
uvicorn backend.service.api:app --port 8000 &
uvicorn backend.service.api:app --port 8001 &
uvicorn backend.service.api:app --port 8002 &
```

Set `UNIGURU_METRICS_STATE_FILE` to a shared path to persist metrics across restarts.

---

## 7. Common Failure Scenarios

### 7.1 KB Not Loading (37 Kosha entries expected)
```
Symptom: /health/ready → "kb_loaded": false
```
Check:
```bash
ls -la backend/data/kosha/
python -c "from kosha.kosha_loader import KoshaLoader; print(len(KoshaLoader(['backend/data/kosha']).load_all()))"
# Expected: 37
```

### 7.2 Rate Limiting Complaints
```
Symptom: Clients receiving 429 errors
```
Fix: Increase rate limit or whitelist IPs
```bash
export UNIGURU_RATE_LIMIT_MAX_REQUESTS=120  # Double default
```

### 7.3 All Responses Are Safe-Fallback
```
Symptom: All /ask responses begin with "I am still learning..."
```
Possible causes:
- Queue saturated: Check `uniguru_router_queue_rejected_total` in /metrics
- Auth misconfigured: Check X-Api-Token header
- LLM unavailable: Check GROQ_API_KEY

### 7.4 High Latency
```
Symptom: p95 > 500ms
```
Check structured logs for slow requests:
```bash
cat logs/uniguru_structured.jsonl | python -c "
import sys, json
for line in sys.stdin:
    e = json.loads(line)
    if e.get('latency_ms', 0) > 500:
        print(e)
"
```

---

## 8. Validation Commands

Run these after any deployment to confirm system health:

```powershell
# 1. Test suite (must be 95/95 passing)
pytest tests/ -o addopts="" --tb=short -q

# 2. Proof log replay
python backend/run_proof_log.py

# 3. Retrieval benchmark
python backend/run_retrieval_benchmark.py

# 4. Performance benchmark
python scripts/benchmark_performance.py

# 5. Full validation capture (all of the above + evidence export)
python scripts/run_validation_capture.py
```

---

## 9. Support Contacts

| Role | Responsibility |
|------|---------------|
| Rajaryan | Runtime integration, system validation |
| Vinayak | Independent testing, functional verification |
| Ashmit (Primary Integrator) | Final ecosystem integration, production handover |

---

*Runbook version 1.1.0 — Updated 2026-06-29*
