# Integration Summary

Sprint: TANTRA Ecosystem Participation
Date: 2026-07-11

---

## What changed

Four live HTTP clients were added to replace local-only ecosystem validators:

1. `TantraRuntimeClient` — submits to Vijay's TANTRA SDK (Runtime, Replay, Trace, Authority, Capability contracts)
2. `InsightFlowClient` — emits traces and decisions to InsightFlow
3. `GCClient` — submits authority and hidden-state payloads to GC
4. `MDUClient` — submits schema and provenance payloads to MDU

`ecosystem_runtime.py` was updated to call all four clients within the existing
7-layer execution pipeline. Each layer now returns both its local result and the
live service response, so reviewers can see exactly what was sent and what was received.

`BucketTelemetryClient` was already live-capable; it is now consistently referenced
alongside the other clients.

---

## What did not change

- No governance logic was modified
- No contracts were duplicated
- No schemas were introduced locally that conflict with MDU
- No bypass of `ConstitutionalCognitionRuntime`
- No new API endpoints (existing `/runtime/ecosystem/execute`, `/runtime/ecosystem/replay`,
  `/mitra/ecosystem/ask` are sufficient)

---

## Activation path

1. Vijay provides `TANTRA_SDK_BASE_URL` + `TANTRA_SDK_TOKEN` → set `TANTRA_SDK_ENABLED=true`
2. Bucket owner provides endpoint + token → set `UNIGURU_BUCKET_TELEMETRY_ENABLED=true`
3. InsightFlow owner provides endpoint + token → set `INSIGHTFLOW_ENABLED=true`
4. GC team provides endpoint + token → set `GC_ENABLED=true`
5. MDU team provides endpoint + token → set `MDU_ENABLED=true`
6. Run `POST /runtime/ecosystem/execute` and confirm all `live: true` responses
7. Run `POST /runtime/ecosystem/replay` and confirm hash stability
8. Capture screenshots of all live service responses
9. Joint certification with Vijay

---

## Risk: execution_hash stability with live responses

The `execution_hash` in `ecosystem_runtime.py` is currently computed after live responses
are attached to the payload. This means the hash will vary if live services return
different data across runs, breaking replay determinism.

**Resolution required from Vijay:** confirm whether live response fields should be
excluded from the hash computation. If yes, the fix is a one-line change in
`execute_ecosystem_runtime()` — compute the hash before attaching live responses.
