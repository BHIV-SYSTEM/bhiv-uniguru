# Bucket Telemetry Integration Report

Date: 2026-03-12

## Implementation
- Added telemetry client:
  - `uniguru/integrations/bucket_telemetry.py`
- Added event emission wiring in API:
  - `uniguru/service/api.py` (`_emit_bucket_events`)
- Emitted events:
  - `router_decision`
  - `knowledge_verified`
  - `knowledge_unverified`
  - `llm_fallback`
  - `workflow_delegation`

## Metadata Contract (No Raw Query)
Each event sends:
- `query_hash`
- `route`
- `verification_status`
- `latency`
- `caller`
- `session_id`
- `event`

Raw query text is never sent to Bucket.

## Configuration
Environment variables added:
- `UNIGURU_BUCKET_TELEMETRY_ENABLED`
- `UNIGURU_BUCKET_TELEMETRY_ENDPOINT`
- `UNIGURU_BUCKET_TELEMETRY_TOKEN`
- `UNIGURU_BUCKET_TELEMETRY_TIMEOUT_SECONDS`

## Validation Status
- Local wiring verified in API path and logs.
- External Bucket endpoint delivery is configuration-dependent and was not reachable from this sandboxed environment.
