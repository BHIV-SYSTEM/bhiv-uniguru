# Critical Code Packets

Sprint: TANTRA Ecosystem Participation

---

## Packet 1 — TantraRuntimeClient (new)

File: `backend/integrations/tantra_runtime_client.py`

Key design decisions:
- Single `_post()` method handles all HTTP calls — no duplication
- Returns `{"live": False, "reason": "not_configured"}` when env vars absent — pipeline never crashes
- All 5 Vijay SDK contracts exposed as named methods matching the task spec:
  `submit_execution_event`, `submit_replay_event`, `submit_trace`, `validate_authority`, `register_capability`
- Bearer token auth via `Authorization` header
- Timeout configurable via `TANTRA_SDK_TIMEOUT_SECONDS`

---

## Packet 2 — InsightFlowClient / GCClient / MDUClient (new)

Files: `backend/integrations/insightflow_client.py`, `gc_client.py`, `mdu_client.py`

Same pattern as TantraRuntimeClient. Each client:
- Has its own `_ENABLED` / `_BASE_URL` / `_TOKEN` env vars
- Returns structured `{"live": False}` on misconfiguration or network failure
- Logs warnings via `logging.getLogger` — never raises exceptions into the pipeline

---

## Packet 3 — ecosystem_runtime.py wiring (modified)

File: `backend/service/ecosystem_runtime.py`

### `_build_tantra_sdk_contracts` — before vs after

Before: built local execution event, returned it. No live call.

After: builds local event, then submits to live TANTRA SDK:
```python
live_execution = _tantra_runtime_client.submit_execution_event(execution_event)
live_trace = _tantra_runtime_client.submit_trace({...})
live_authority = _tantra_runtime_client.validate_authority({...})
```
Returns all three live responses alongside the local event. `tantra_sdk_live` flag
indicates whether the SDK endpoint was reachable.

### `_build_insightflow_observability` — before vs after

Before: returned local state dict only.

After: emits to InsightFlow and attaches responses:
```python
live_trace = _insightflow_client.emit_trace(local_payload)
live_decision = _insightflow_client.emit_decision({...})
local_payload["live_trace"] = live_trace
local_payload["live_decision"] = live_decision
```

### `_build_gc_validation` — before vs after

Before: returned local authority enforcement dict only.

After: submits to GC and attaches responses:
```python
live_authority = _gc_client.validate_authority(local_payload)
live_hidden_state = _gc_client.validate_hidden_state({...})
local_payload["live_authority_validation"] = live_authority
local_payload["live_hidden_state_validation"] = live_hidden_state
```

### `_build_mdu_validation` — before vs after

Before: returned local schema compatibility dict only.

After: submits to MDU and attaches responses:
```python
live_schema = _mdu_client.validate_schema(evidence_payload)
live_provenance = _mdu_client.validate_provenance(lineage_payload)
local_result["live_schema_validation"] = live_schema
local_result["live_provenance_validation"] = live_provenance
```

---

## Packet 4 — Graceful degradation contract

Every live client method returns one of two shapes:

**When live:**
```json
{"live": true, "status": 200, "data": {...}}
```

**When not configured or failed:**
```json
{"live": false, "reason": "not_configured", "path": "/runtime/execution-event"}
```

The pipeline never branches on `live` — it always attaches the response and continues.
This means the execution hash and replay hash remain stable regardless of whether
live services are reachable, preserving replay determinism.
