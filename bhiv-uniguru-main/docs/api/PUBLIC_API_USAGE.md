# PUBLIC_API_USAGE

## Base URL
`https://uni-guru.in`

## Authentication
All requests to protected endpoints MUST include the `Authorization` header:
`Authorization: Bearer <your_access_token>`

## Caller Identification
Callers MUST identify themselves via:
- JSON field: `context.caller`
- OR Header: `X-Caller-Name`

Supported callers: `bhiv-assistant`, `gurukul-platform`, `internal-testing`.

## Endpoints

### 1. Ask (POST /ask)
Primary reasoning endpoint.
**Payload:**
```json
{
  "query": "What is ahimsa?",
  "context": {
    "caller": "bhiv-assistant"
  },
  "allow_web": false
}
```

### 2. Health (GET /health)
Public health status (no auth).
```json
{
  "status": "ok",
  "service": "uniguru-live-reasoning",
  "version": "1.1.0"
}
```

### 3. Metrics (GET /metrics)
Prometheus compatible metrics (requires auth).

### 4. Dashboard (GET /monitoring/dashboard)
Structured live dashboard data (requires auth).
