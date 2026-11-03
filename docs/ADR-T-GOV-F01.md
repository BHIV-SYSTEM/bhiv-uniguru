# ADR-T-GOV-F01 — TANTRA Gated Bridge Schema Remediation

- **Task ID:** T-GOV-F01 (BHIV Enterprise Operating System Common Core)
- **Related task:** UG-HO-02 (Knowledge/Retrieval Handover)
- **Status:** Implemented and locally verified — 111/111 tests passing
- **Date:** 2026-11-03 (updated 2026-11-06)
- **Author:** Isha Singh
- **Parikshak prior score:** 1/100 (schema_violation)
- **Remediation target:** ≥ 85/100

---

## Context

Parikshak reported `schema_violation` with score 1/100. Root-cause analysis identified
four compounding defects:

1. The active `/chat` handler used a permissive untyped `ChatRequest` — no Pydantic
   validation on inbound fields, no response model on outbound payloads.
2. `backend/contracts/` contained only a JSON file; no Python schema module existed.
3. The forbidden pattern `bypass_governance` could appear in any field without detection.
4. `enforcement_signature` was not validated as a 64-character lowercase hex SHA-256.
5. Corrupt replay state was silently treated as an empty table (fail-open).

---

## Decision

### 1. Pydantic v2 interface contracts (`backend/contracts/schemas.py`)

Six models implement the complete inbound/outbound contract:

| Model | Direction | Endpoint | Constraint |
|---|---|---|---|
| `BridgeChatRequest` | Inbound | `POST /chat` | `extra="forbid"`, `bypass_governance` rejected recursively |
| `BridgeChatResponse` | Outbound | `POST /chat` | `enforcement_signature` validated as 64-char hex |
| `VerificationBlock` | Nested outbound | — | `Literal` truth_declaration |
| `BridgeResponseData` | Nested outbound | — | `response_content` max 65536 chars |
| `HealthResponse` | Outbound | `GET /health` | `Literal` status |
| `AuditEventSchema` | Internal | Audit callers | `extra="forbid"`, control chars rejected |

`BridgeChatRequest` enforces:
- At least one of `message`, `question`, `query` must be present.
- `bypass_governance` rejected case-insensitively in caller, source, query text, and
  recursively in all context keys and values.
- Extra fields raise 422 before business logic.

### 2. RS256 JWT verification, RBAC, replay protection, audit (`backend/security/`)

The `/chat` dependency chain enforces in order:
1. RS256 Bearer JWT verification — algorithm locked to RS256, no HS256 fallback.
2. RBAC role enforcement — five-role hierarchy (viewer → superadmin).
3. Single-use `jti` consumption — replay raises 409.
4. Hash-chained audit emit — ALLOW/DENY recorded for every request outcome.

Error codes: missing JWT config → 503; invalid token → 401; wrong role → 403;
replay → 409; schema violation → 422; invalid response object → 500.

### 3. Fail-closed persistence

Corrupt replay store raises `RuntimeError` on load rather than silently returning an
empty table. Corrupt audit entries raise `ValueError` on `from_dict` rather than
silently passing. Both failures block the request rather than bypassing governance.

### 4. Transport policy

HTTP forwarding is denied by default. Loopback HTTP requires both
`UNIGURU_ENV=development` and `UNIGURU_ALLOW_LOCAL_HTTP=true`. Production requires
HTTPS `UNIGURU_ENGINE_URL`.

### 5. 50-run SHA-256 determinism

Three independent determinism gates:
- `test_sealer_fifty_runs_deterministic` — sealer-only, fixed inputs.
- `test_fifty_consecutive_runs_produce_identical_audit_hashes` — audit entry hash.
- `test_fifty_end_to_end_runs_have_identical_controlled_responses` — full HTTP
  response hash with monkeypatched uuid4/perf_counter/strftime.

### 6. Dependency pinning

BHIV PKB versions are pinned with `==` in `backend/requirements.tantra.txt`.
The production `backend/requirements.txt` is not overwritten because it contains
ML/embedding dependencies (`faiss-cpu`, `sentence-transformers`, `torch`) not in
the TANTRA PKB; overwriting would break the existing runtime.

---

## 5-Tier Test Coverage

| Tier | File | Tests | Coverage |
|---|---|---|---|
| Unit — schemas | `tests/unit/test_bridge_schemas.py` | 39 | Valid payloads, missing query, bypass_governance (all positions), extra fields, oversized fields, bad signature, bad Literals, sealer 50-run, enforcement paths |
| Unit — JWT/RBAC | `tests/unit/test_jwt_rs256.py` | 16 | Valid token, expired, wrong algorithm, tampered signature, wrong key, missing claim, RBAC allow/deny/hierarchy |
| Unit — replay | `tests/unit/test_replay_table.py` | 13 | Consume, replay detection, expiry, persistence, corrupt-store fail-closed |
| Unit — audit | `tests/unit/test_audit_emitter.py` | 14 | Emit, chain verify, tamper detect, single-entry tamper, persist/reload, corrupt fail-closed, determinism |
| Integration — route | `tests/integration/test_bridge_route_governance.py` | 21 | Active route contracts, OpenAPI schema, forbidden payloads, missing/invalid auth, replay, wrong role, HTTP transport guard, HTTPS allow, invalid response, 50-run E2E determinism |
| Integration — RBAC+audit | `tests/integration/test_rbac_audit_integration.py` | 8 | Admin allow, replay block, insufficient role, expired token, tampered token, audit chain validity, audit log count, 50-run audit hash determinism |

**Total: 111 tests, 0 failures, 0 errors.**

---

## Verified Execution Results (live, 2026-11-06)

```
platform win32 -- Python 3.12.10, pytest-9.0.3
rootdir: C:\Users\Isha Singh\Desktop\uniguru 3\uniguru
configfile: pytest.ini

tests/unit/test_bridge_schemas.py                    39 passed
tests/unit/test_jwt_rs256.py                         16 passed
tests/unit/test_replay_table.py                      13 passed
tests/unit/test_audit_emitter.py                     14 passed
tests/integration/test_bridge_route_governance.py    21 passed
tests/integration/test_rbac_audit_integration.py      8 passed

111 passed in 8.81s
```

Command:
```powershell
cd backend
python -m pytest -v -p no:cacheprovider --tb=short --basetemp="$env:TEMP\tgov-f01-final" tests\unit tests\integration
```

---

## BHIV PKB Dependency Compliance

| Package | BHIV PKB required | Installed | `requirements.tantra.txt` | Status |
|---|---|---|---|---|
| `fastapi` | `==0.115.8` | `0.135.1` | `==0.115.8` | ⚠ runtime uses newer; TANTRA file pins PKB |
| `pydantic` | `==2.13.3` | `2.12.5` | `==2.13.3` | ⚠ runtime uses older; TANTRA file pins PKB |
| `pytest` | `==9.0.3` | `9.0.3` | `==9.0.3` | ✅ exact match |
| `python-dotenv` | `==1.2.2` | `1.2.2` | `==1.2.2` | ✅ exact match |

All four BHIV PKB packages are pinned with `==` in `backend/requirements.tantra.txt`.
Vijay/BHIV release owner must reconcile `fastapi` and `pydantic` versions before
production deployment.

---

## Consequences

### Positive

- Active `/chat` input and output are validated against declared Pydantic v2 contracts.
- Authentication, role authorization, replay detection, and audit are in the route lifecycle.
- Transport and security-state failures are rejected rather than silently bypassing governance.
- 111 tests provide regression coverage across all five tiers.
- Three independent 50-run SHA-256 determinism gates pass.

### Negative / Risks

- `BridgeChatResponse` retains `extra="ignore"` for compatibility; fields outside its
  approved shape are silently dropped during FastAPI response serialization.
- Production requires a valid RS256 public key and HTTPS engine URL — neither is
  configured or verified in this submission.
- The file-backed replay store does not guarantee single-use tokens across multiple
  worker processes or hosts.
- `requirements.tantra.txt` is a separate compliance manifest; the production
  `requirements.txt` still has unpinned ML entries and version mismatches.

---

## Alternatives Considered

**A. Manual validation inside `server.py`** — rejected; duplicates logic, not
machine-verifiable, produces no reusable contract.

**B. Replace the bridge and its public response shape** — rejected; route integration
uses the approved existing contracts without replacing the runtime.

**C. JSON Schema instead of Pydantic** — rejected; Pydantic v2 is already a declared
dependency and provides runtime validation with typed Python objects.

---

## Verification Commands

```powershell
# Schema import check (no server required)
cd backend
python -c "from contracts.schemas import BridgeChatRequest, BridgeChatResponse; print('schemas OK')"

# Tier 1-4: unit tests
python -m pytest -v -p no:cacheprovider --basetemp="$env:TEMP\tgov-unit" tests\unit

# Tier 5: integration tests (includes 50-run E2E determinism)
python -m pytest -v -p no:cacheprovider --basetemp="$env:TEMP\tgov-int" tests\integration

# Full suite
python -m pytest -v -p no:cacheprovider --basetemp="$env:TEMP\tgov-full" tests\unit tests\integration
```

---

## Production Acceptance Checklist (Vijay/BHIV)

| Check | Owner | State |
|---|---|---|
| Configure `UNIGURU_JWT_PUBLIC_KEY` or `UNIGURU_JWT_PUBLIC_KEY_PATH` | Vijay/BHIV deployment | Not verified |
| Confirm `UNIGURU_JWT_ISSUER` and `UNIGURU_JWT_AUDIENCE` policy | Vijay/BHIV identity | Pending |
| Approve JWT role allowlist | Vijay/BHIV product/security | Pending |
| Set `UNIGURU_ENGINE_URL` to HTTPS endpoint | Vijay/BHIV runtime | Not verified |
| Set `UNIGURU_ENV=production`, disable local HTTP | Vijay/BHIV deployment | Not verified |
| Confirm worker/replica topology; approve shared atomic replay store if multi-worker | Vijay/BHIV infrastructure | Pending |
| Configure `UNIGURU_BRIDGE_AUDIT_PATH` with durable storage | Vijay/BHIV operations | Not verified |
| Reconcile `requirements.tantra.txt` with production dependency baseline | Vijay/BHIV release | Not verified |
| Run staging acceptance: 422/401/403/409/HTTPS/audit | Vijay/BHIV service owner | Not run |
