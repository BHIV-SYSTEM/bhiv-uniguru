# ADR-T-GOV-F01 — TANTRA Gated Bridge Schema Remediation

- **Task ID:** T-GOV-F01 / UG-HO-02
- **Status:** Implemented locally; deployment configuration remains unverified
- **Date:** 2026-11-03
- **Author:** Isha Singh

---

## Context

Parikshak reported `schema_violation`. The immediate integration defect was that the active `/chat` handler still used a separate permissive `ChatRequest`, had no response model, and did not declare the security components in its request lifecycle. The Pydantic contracts existed in the working tree but did not govern actual requests or responses. A second fail-open risk was that corrupt replay state could be silently treated as an empty replay table.

---

## Decision

### 1. Bind the existing Pydantic v2 contracts to `/chat`

The active route now uses `BridgeChatRequest` and declares `BridgeChatResponse` as its FastAPI response model. FastAPI validates inbound request fields and serializes the outbound response against those contracts. OpenAPI now advertises both schemas and HTTP Bearer security.

The request validator rejects the forbidden marker in message/question/query text, caller/source values, and recursively in nested context keys and values. Other content is not rejected by a generic keyword or URL heuristic.

The existing models include:

| Model | Direction | Endpoint |
|---|---|---|
| `BridgeChatRequest` | Inbound | `POST /chat` |
| `BridgeChatResponse` | Outbound | `POST /chat` |
| `VerificationBlock` | Nested outbound | — |
| `BridgeResponseData` | Nested outbound | — |
| `HealthResponse` | Outbound | `GET /health` |
| `AuditEventSchema` | Internal | Audit emitter callers |

### 2. Enforce authentication, authorization, replay protection, and audit

The `/chat` dependency verifies RS256 Bearer JWTs, applies the existing role allowlist, and consumes each token `jti` before business logic. Missing JWT configuration fails with 503; invalid credentials fail with 401, disallowed roles with 403, and replays with 409. Middleware writes hash-chained ALLOW/DENY audit entries for successful and rejected `/chat` attempts, including request-schema failures. Tokens, request text, and context contents are not written to the audit log.

Replay and audit persistence read errors now fail closed rather than silently appearing as empty stores. The replay table is thread-safe within one process; it does not provide atomic replay exclusion across multiple worker processes or hosts.

### 3. Enforce transport policy at the forwarding boundary

The default target remains `http://127.0.0.1:8000/ask`, but forwarding to HTTP is denied by default, including in production. Loopback HTTP is permitted only with both `UNIGURU_ENV=development` and `UNIGURU_ALLOW_LOCAL_HTTP=true`, and only for localhost/loopback addresses. Production forwarding therefore requires an HTTPS `UNIGURU_ENGINE_URL`. No live deployment URL or HTTPS connectivity was verified.

### 4. Production configuration and acceptance

Before production, the service owner must provide and verify:

- An RS256 public key through `UNIGURU_JWT_PUBLIC_KEY` or `UNIGURU_JWT_PUBLIC_KEY_PATH`. Keep the signing private key exclusively with the authorized issuer; do not put it in this repository, service environment, or review evidence. Protect the configured public-key value/file against unauthorized replacement. The verifier supports optional issuer and audience restrictions through `UNIGURU_JWT_ISSUER` and `UNIGURU_JWT_AUDIENCE`; Vijay/BHIV must confirm the deployment values and whether both restrictions are mandatory.
- An HTTPS `UNIGURU_ENGINE_URL` that is reachable from the deployed bridge and whose TLS certificate validates in that environment. The default loopback HTTP target is not a production-ready endpoint. Set `UNIGURU_ENV=production` and ensure `UNIGURU_ALLOW_LOCAL_HTTP` is absent or false. No actual deployment URL, certificate, or connectivity has been checked.
- A confirmed JWT role allowlist. The current bridge accepts the five roles configured in code; Vijay/BHIV must approve that policy against the caller population.
- Writable, durable, access-controlled storage for `UNIGURU_BRIDGE_AUDIT_PATH` and, for single-process deployments only, `UNIGURU_REPLAY_STORE_PATH`. Keep credentials and raw JWTs out of audit metadata. Define audit retention, integrity verification, and chain-aware archival before rotation; truncating the active chain invalidates continuity.
- A deployment topology decision for replay protection. The current replay table persists JSON and locks threads only within a process. For multiple workers/replicas, use an approved shared atomic store with compare-and-set/insert-if-absent semantics and expiry tied to token expiration plus policy leeway. A non-atomic read-then-write or per-process store is insufficient. No shared-store integration is implemented here.
- A tested dependency resolution plan. `requirements.tantra.txt` is a strict, separate test/compliance manifest; the broader runtime manifest remains distinct. The deployer must resolve any version differences against the approved TANTRA and runtime baselines rather than assuming this test passed against production packages.

### 5. End-to-end determinism scope

The route-level 50-run test sends the same request body through FastAPI with controlled engine, clock, and trace-ID dependencies, while using fresh valid token IDs to avoid replay rejection. It compares SHA-256 hashes of complete serialized responses. Audit timestamps and sequence numbers are external side effects and are not part of the HTTP response hash. The existing sealer-only determinism test remains a separate, narrower check.

### 6. `requirements.txt` pinning

The TANTRA PKB specifies exact versions. The existing `backend/requirements.txt` uses unpinned entries for `faiss-cpu`, `sentence-transformers`, and `torch`, and has version mismatches on `fastapi`, `uvicorn`, `pydantic`, `cryptography`, `requests`, and `pytest`. A TANTRA-compliant pinned file is maintained at `backend/requirements.tantra.txt`. The production `requirements.txt` is not overwritten because it contains additional runtime dependencies not in the TANTRA PKB; overwriting it would break the existing runtime.

---

## Consequences

### Positive

- Active `/chat` input and output are validated against the declared contracts.
- Authentication, role authorization, replay detection, and audit are in the route lifecycle.
- Transport and security-state failures are rejected rather than silently bypassing governance.

### Negative / Risks

- `BridgeChatResponse` retains `extra = "ignore"` for compatibility; fields outside its approved shape are removed during FastAPI response serialization.
- Production must provide a valid `UNIGURU_JWT_PUBLIC_KEY` or key path and an HTTPS `UNIGURU_ENGINE_URL`.
- The existing file replay store does not guarantee single-use tokens across multiple processes.
- `requirements.tantra.txt` is a separate file; the production `requirements.txt` still has unpinned entries for ML dependencies.
- Production approval is blocked until owners verify key configuration, issuer/audience and role policy, TLS connectivity, durable audit storage, and topology-appropriate replay prevention.

---

## Alternatives considered

**A. Validate inside `server.py` with manual checks** — rejected because it duplicates logic, is not machine-verifiable, and does not produce a reusable contract.

**B. Replace the bridge and its public response shape** — rejected; route integration uses the approved existing contracts without replacing the runtime.

**C. Use JSON Schema instead of Pydantic** — rejected; Pydantic v2 is already a declared dependency and provides runtime validation with typed Python objects.

---

## Verification

```powershell
# Schema unit tests
python -m pytest -q backend/tests/unit/test_bridge_schemas.py

# Active route, auth, replay, audit, transport, OpenAPI, and 50-run tests
python -m pytest -q backend/tests/integration/test_bridge_route_governance.py

# Full security + determinism suite
python -m pytest -q -p no:cacheprovider --basetemp="$env:TEMP\tgov-full-suite-final3" backend/tests/unit backend/tests/integration

# Schema import check (no server required)
python -c "from contracts.schemas import BridgeChatRequest, BridgeChatResponse; print('schemas OK')"
```

The recorded local results are 103 passed for the focused bridge/security selection and 111 passed for all backend unit and integration tests. These are local results, not deployment or production-acceptance evidence.
