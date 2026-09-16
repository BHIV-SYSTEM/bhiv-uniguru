# UniGuru Canonical API Contract (BHIV Ecosystem)

## Service
- Name: `uniguru-live-reasoning`
- Base path: `/`
- Primary endpoint: `POST /ask`

## Request Contract
```json
{
  "query": "What is ahimsa?",
  "context": {
    "caller": "bhiv-assistant",
    "channel": "api"
  },
  "allow_web": false,
  "session_id": "optional-session-id"
}
```

### Request Fields
- `query` (string, required): user query payload.
- `context` (object, optional): caller-provided metadata map.
- `context.caller` OR `X-Caller-Name` header (required for `POST /ask`): caller identity used for allowlist checks.
- `allow_web` (boolean, optional, default `false`): permits web fallback when allowed by governance and verification.
- `session_id` (string, optional): caller correlation identifier.

### Validation Rules
- Extra fields are rejected.
- Empty query is rejected.
- Query length capped at 2000 chars.
- Context size limited (max 64 keys, max 8KB serialized).
- Unsupported control characters are rejected.
- Caller is required via `context.caller` or `X-Caller-Name`.
- Caller must be in the allowed set (`bhiv-assistant`, `gurukul-platform`, `internal-testing`) unless overridden by env config.

## Authentication
- Protected endpoints require Bearer token authentication:
  - `POST /ask`
  - `GET /metrics`
  - `POST /metrics/reset`
  - `GET /monitoring/dashboard`
- Health/readiness endpoints remain probeable without auth:
  - `GET /health`
  - `GET /ready`
  - `GET /health/ready`
  - `GET /health/live`

### Auth Headers
Use either:
- `Authorization: Bearer <token>`
- `X-Service-Token: <token>`

### Auth Environment Variables
- `UNIGURU_API_AUTH_REQUIRED` (`true|false`)
- `UNIGURU_API_TOKEN` (primary single token)
- `UNIGURU_API_TOKENS` (optional comma-separated fallback/rotation tokens)
- `UNIGURU_ALLOWED_CALLERS` (comma-separated caller allowlist)

## Response Contract
```json
{
  "decision": "answer",
  "answer": "UniGuru Deterministic Knowledge Retrieval: ...",
  "session_id": "optional-session-id",
  "reason": "Knowledge found in local KB and verified.",
  "ontology_reference": {
    "concept_id": "uuid",
    "domain": "quantum",
    "snapshot_version": 1,
    "snapshot_hash": "sha256...",
    "truth_level": 3
  },
  "reasoning_trace": {
    "sources_consulted": ["quantum", "ontology_registry", "ontology_graph"],
    "retrieval_confidence": 0.92,
    "ontology_domain": "quantum",
    "verification_status": "VERIFIED",
    "verification_details": "VERIFIED"
  },
  "governance_output": {
    "allowed": true,
    "reason": "Output governance passed.",
    "flags": {}
  },
  "verification_status": "VERIFIED",
  "enforcement_signature": "sha256...",
  "status_action": "ALLOW",
  "request_id": "uuid",
  "sealed_at": "2026-03-07T00:00:00Z",
  "latency_ms": 12.4
}
```

### Response Fields (Required for System Integration)
The following fields MUST be present and correctly typed in every successful `2xx` response:
- `decision` (string): The final action taken by the system (`answer`, `block`).
- `answer` (string): The generated response content or refusal message.
- `ontology_reference` (object): Metadata linking the response to a specific concept in the UniGuru ontology.
- `verification_status` (string): One of `VERIFIED`, `PARTIAL`, `UNVERIFIED`.
- `reasoning_trace` (object): Details of the sources consulted and confidence scores.
- `governance_output` (object): Results of the output governance checks.
- `enforcement_signature` (string): Cryptographic seal ensuring response integrity.
- `request_id` (string): Unique identifier for the transaction.
- `latency_ms` (float): Processing time in milliseconds.

## Health and Observability Endpoints
UniGuru exposes standard health and metrics endpoints for infrastructure monitoring:
- `GET /health`: Returns overall service status and sub-component health.
- `GET /ready`: Readiness probe for load balancers.
- `GET /metrics`: Prometheus-compatible runtime metrics (RPM, success rate, latency).
- `GET /monitoring/dashboard`: JSON-structured live dashboard data.

## Error Statuses
- `422` for malformed request payloads.
- `429` when request rate limit is exceeded.
- `404` for unknown ontology concept lookup.
- `401` for missing/invalid token on protected endpoints.
- `403` for unknown callers on `/ask`.

## Backward Compatibility
- Legacy fields are accepted and mapped:
  - `user_query` -> `query`
  - `allow_web_retrieval` -> `allow_web`
