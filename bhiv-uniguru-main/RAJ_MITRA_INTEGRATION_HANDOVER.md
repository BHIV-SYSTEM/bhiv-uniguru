# UniGuru API - Mitra Integration Handover

Priority: P1
Owner: Vijay + Isha
Generated: 2026-06-25

## Current Status

The current public Render URL did not respond from this execution environment:

```text
GET  https://uniguru-v2.onrender.com/health     -> timed out
POST https://uniguru-v2.onrender.com/ask        -> timed out
POST https://uniguru-v2.onrender.com/new_query  -> timed out
```

The latest backend codebase is now locally validated and deployable. The fastest path for Raj is to redeploy the Render service from this repo, then use the contract below.

## Working Codebase

Repo:

```text
C:\Users\Yass0\OneDrive\Desktop\uniguru_3\uniguru_v2-main
```

Backend app:

```text
backend/service/api.py
```

Deployment config:

```text
Dockerfile
render.yaml
```

Render service name in `render.yaml`:

```text
uniguru-api
```

Expected production base URL after redeploy:

```text
https://uniguru-v2.onrender.com
```

## Fixes Applied For Recovery

1. Docker startup points at the correct FastAPI app:

```text
uvicorn service.api:app
```

2. Supabase auth is now optional when Supabase is not configured, so Mitra API startup is not blocked by missing Supabase auth packages in no-auth deployments.

3. Backend retrieval imports now explicitly use `backend.retrieval.*` where required, avoiding collision with the top-level curriculum `retrieval/` package.

## Redeploy Instructions

Use Render dashboard:

1. Open Render service `uniguru-api`.
2. Confirm it is connected to this repo/branch.
3. Confirm Docker deployment uses:

```text
Dockerfile
```

4. Confirm env vars:

```text
PYTHONPATH=/app/backend
UNIGURU_HOST=0.0.0.0
UNIGURU_PORT=8000
UNIGURU_WORKERS=1
UNIGURU_API_AUTH_REQUIRED=false
UNIGURU_ALLOWED_CALLERS=*
EXTERNAL_API_SECRET_KEY=uniguru_secret_123
UNIGURU_ROUTER_QUEUE_LIMIT=100
UNIGURU_ROUTER_UNVERIFIED_FALLBACK=false
ENABLE_BUCKET_TELEMETRY=false
ENABLE_CORE_READER=false
ENABLE_STT=true
LOG_LEVEL=INFO
```

5. Click Manual Deploy -> Deploy latest commit.
6. Verify:

```bash
curl https://uniguru-v2.onrender.com/health
```

## Primary Mitra Endpoint

Use this endpoint once Render is redeployed:

```text
POST https://uniguru-v2.onrender.com/new_query
```

Authentication:

```text
Authorization: Bearer uniguru_secret_123
Content-Type: application/json
```

Sample request:

```bash
curl -X POST https://uniguru-v2.onrender.com/new_query \
  -H "Authorization: Bearer uniguru_secret_123" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the significance of the Bhagavad Gita?",
    "request_id": "mitra-req-001",
    "intent": "information_retrieval",
    "context": {
      "caller": "mitra",
      "user_id": "mitra-user-001"
    },
    "required_outputs": ["signals", "final_answer"]
  }'
```

Raj should read these response fields:

```text
answer
verification_status
confidence
trace_id
matched_signals
output_contract
downstream_execution
```

## Simpler Backup Endpoint

If Raj needs immediate low-friction integration:

```text
POST https://uniguru-v2.onrender.com/ask
```

Auth:

```text
No auth required when UNIGURU_API_AUTH_REQUIRED=false.
```

Sample request:

```bash
curl -X POST https://uniguru-v2.onrender.com/ask \
  -H "Content-Type: application/json" \
  -H "X-Caller-Name: mitra" \
  -d '{
    "query": "What is karma?",
    "context": {
      "caller": "mitra",
      "user_id": "mitra-user-001"
    }
  }'
```

Raj should read:

```text
answer
verification_status
decision
request_id
reasoning_trace
routing
```

## Local Proof Of Successful API Execution

Executed against the exact FastAPI app via `TestClient` after startup fixes:

```text
GET  /health     -> 200
POST /ask        -> 200
POST /new_query  -> 200
```

Health response proof:

```json
{
  "status": "ok",
  "service": "uniguru-live-reasoning",
  "version": "1.1.0",
  "checks": {
    "ontology_registry": "ok",
    "reasoning_service": "ok",
    "router_active": true,
    "kb_loaded": true,
    "llm_available": true
  },
  "auth": {
    "required": false,
    "mode": "disabled"
  }
}
```

`/ask` proof:

```text
Status: 200
Answer preview: Based on verified source: jain_karma_doctrine.md
Verification status: VERIFIED
```

`/new_query` proof:

```text
Status: 200
Response fields included: answer, confidence, confidence_breakdown, matched_signals,
output_contract, downstream_execution, trace_id, verification_status
Answer preview: I do not have verified knowledge to answer this question.
```

## Timeout Behaviour

Recommended Mitra client timeout:

```text
25 seconds
```

Backend guardrails:

```text
Rate limit: 60 requests/min/IP by default
Queue limit: 100 configured in render.yaml
Health path: /health
Readiness path: /health/ready
Liveness path: /health/live
```

## Immediate Raj Integration Steps

1. Wait for Render redeploy to complete.
2. Confirm `GET /health` returns `status: ok`.
3. Integrate Mitra with `POST /new_query` using bearer token.
4. If Mitra only needs answer text first, use `POST /ask`.
5. Log `trace_id` or `request_id` per request.
6. Treat public Render timeout as deployment availability, not endpoint contract failure.
