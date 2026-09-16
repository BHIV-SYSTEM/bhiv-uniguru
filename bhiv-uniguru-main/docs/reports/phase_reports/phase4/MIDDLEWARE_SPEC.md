# UniGuru Middleware Bridge Specification (Phase 4)

## 1. Objective
To provide a deterministic HTTP interface for the Rule-Based Language Model (RLM v1), serving as a safety-first admission gateway between the user and the legacy generative systems.

## 2. Decision Contract
The bridge server evaluates every request against the deterministic rule tiers and returns a standardized decision object.

### Decision States:
| Decision | HTTP Code | Meaning |
| :--- | :--- | :--- |
| `ALLOW` | 200 | Continue to next gate (Internal state). |
| `BLOCK` | 403 | Request rejected (Safety/Authority violation). |
| `ANSWER`| 200 | Terminal response found in KB or via Rule (Deterministic). |
| `FORWARD`| 200 | Safe request, handover to Legacy Generative AI. |

## 3. Communication Schema

### Request Payload (POST /admit)
```json
{
  "request_content": "string",
  "metadata": {
    "user_id": "string",
    "session_id": "string",
    "timestamp": "iso-8601"
  }
}
```

### Response Schema
```json
{
  "request_id": "uuid",
  "decision": "BLOCK | ANSWER | FORWARD",
  "reason": "string",
  "response_content": "string | null",
  "rule_triggered": "string",
  "latency_ms": 12.5,
  "trace": {
    "rules": ["list", "of", "traces"],
    "retrieval": "retrieval_trace_object | null"
  }
}
```

## 4. Bridge Logic Workflow

1.  **Ingress**: Receive `POST /admit`.
2.  **Engine Execution**: Call `RuleEngine.evaluate(request_content)`.
3.  **Trace Harvest**: Capture rule and retrieval traces.
4.  **Action Dispatch**:
    *   If `BLOCK` or `ANSWER` -> Return response immediately.
    *   If `FORWARD` -> Call Legacy Proxy + Handover payload.
5.  **Logging**: Write to `bridge_access.log` in a flat JSON format.

## 5. Security & Isolation
- **Stateless**: No caching or session storage in the bridge.
- **Payload Immutability**: The bridge MUST NOT modify the `request_content` sent to the legacy system.
- **Fail-Safe**: If the RuleEngine errors, the default action is `BLOCK` with a 500 error.

## 6. Success Metrics
- **99th Percentile Latency**: < 50ms (Bridge overhead).
- **Match Accuracy**: 100% parity with `rlm_harness.py`.
- **Zero Hallucination**: No generative content allowed in `ANSWER` paths.
