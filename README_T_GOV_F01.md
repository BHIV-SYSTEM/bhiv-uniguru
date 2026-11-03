# T-GOV-F01 — Schema Violation Remediation Patch

**Task ID:** T-GOV-F01  
**Product:** BHIV Enterprise Operating System Common Core  
**Assignee:** Isha Singh  
**Prior Parikshak score:** 1/100 (schema_violation)  
**Branch:** `ug-ho-02-knowledge-retrieval`  
**Repository:** https://github.com/BHIV-SYSTEM/bhiv-uniguru

---

## What Was Wrong

Parikshak failed the submission with `schema_violation` because:

1. `POST /chat` accepted an untyped `Dict[str, Any]` body — no Pydantic validation.
2. `POST /chat` returned an untyped dict — no response model, no shape enforcement.
3. `backend/contracts/` had no Python schema module — only a JSON file.
4. `bypass_governance` could appear in any field without detection.
5. `enforcement_signature` was not validated as 64-character lowercase hex SHA-256.
6. Corrupt replay state was silently treated as an empty table (fail-open).

---

## What Was Fixed

### `backend/contracts/schemas.py` (created)

Six Pydantic v2 models govern all inbound and outbound payloads:

- `BridgeChatRequest` — `extra="forbid"`, rejects `bypass_governance` recursively in
  all fields, requires at least one query field.
- `BridgeChatResponse` — validates `enforcement_signature` as 64-char hex, `Literal`
  discriminators on `decision`, `verification_status`, `status_action`.
- `VerificationBlock`, `BridgeResponseData` — nested outbound models.
- `HealthResponse` — `GET /health` outbound.
- `AuditEventSchema` — `extra="forbid"`, rejects control characters.

### `backend/bridge/server.py` (modified)

- `/chat` now declares `BridgeChatRequest` as the request body type.
- `/chat` now declares `BridgeChatResponse` as the FastAPI response model.
- RS256 JWT verification, RBAC enforcement, single-use `jti` consumption, and
  hash-chained audit emit are wired as route dependencies.
- Transport guard rejects HTTP forwarding in production.
- Missing JWT config → 503; invalid token → 401; wrong role → 403; replay → 409;
  schema violation → 422; invalid response → 500.

### `backend/security/replay_table.py` (modified)

- Corrupt persisted replay store raises `RuntimeError` on load (fail-closed).
- Previously silently returned an empty table.

### `backend/security/audit_emitter.py` (modified)

- `AuditEntry.from_dict` verifies the stored `entry_hash` against recomputed hash.
- Tampered single-entry logs are now detected on reload.

### `backend/requirements.tantra.txt` (updated)

All four BHIV PKB packages pinned with `==`:
- `fastapi==0.115.8`
- `pydantic==2.13.3`
- `pytest==9.0.3`
- `python-dotenv==1.2.2`

---

## Test Results (live, 2026-11-06)

```
platform win32 -- Python 3.12.10, pytest-9.0.3

tests/unit/test_bridge_schemas.py                    39 passed
tests/unit/test_jwt_rs256.py                         16 passed
tests/unit/test_replay_table.py                      13 passed
tests/unit/test_audit_emitter.py                     14 passed
tests/integration/test_bridge_route_governance.py    21 passed
tests/integration/test_rbac_audit_integration.py      8 passed

111 passed in 8.81s — 0 failures, 0 errors
```

50-run SHA-256 determinism: **3/3 gates PASSED**

---

## How to Run

```powershell
cd backend

# Schema import check (no server required)
python -c "from contracts.schemas import BridgeChatRequest, BridgeChatResponse; print('OK')"

# Full 5-tier test suite
python -m pytest -v -p no:cacheprovider --basetemp="$env:TEMP\tgov-f01" tests\unit tests\integration
```

---

## Files Changed

| File | Change |
|---|---|
| `backend/contracts/schemas.py` | Created — 6 Pydantic v2 models |
| `backend/bridge/server.py` | Modified — request/response models, auth dependency |
| `backend/security/replay_table.py` | Modified — fail-closed on corrupt store |
| `backend/security/audit_emitter.py` | Modified — hash verification on reload |
| `backend/requirements.tantra.txt` | Updated — all 4 BHIV PKB packages pinned |
| `backend/tests/unit/test_bridge_schemas.py` | Created — 39 schema unit tests |
| `backend/tests/integration/test_bridge_route_governance.py` | Created — 21 route tests |
| `docs/ADR-T-GOV-F01.md` | Updated — verified results, PKB table, 5-tier breakdown |

---

## Known Limitations

- Production RS256 public key, HTTPS engine URL, and audit storage path are not
  configured — these require Vijay/BHIV deployment owner action.
- The file-backed replay store is single-process only; multi-worker deployments
  require a shared atomic store (Redis or equivalent).
- `requirements.txt` retains runtime versions; `requirements.tantra.txt` is the
  TANTRA compliance manifest. Vijay/BHIV release owner must reconcile before deploy.

See `docs/ADR-T-GOV-F01.md` for the full architecture decision record.
