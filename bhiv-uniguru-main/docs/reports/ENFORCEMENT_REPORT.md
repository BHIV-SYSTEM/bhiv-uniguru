# ENFORCEMENT_SIGNATURE_REPORT

Date: February 27, 2026

## Implementation

Cryptographic sealing is enforced in `uniguru/enforcement/seal.py`:

- Formula: `SHA256(response_content + request_id)`
- Signature field: `enforcement_signature`

Bridge verification gate in `uniguru/bridge/server.py`:

- Bridge calls `enforcer.verify_bridge_seal(sealed_response)` before return.
- If missing/invalid signature: HTTP 500 (`Enforcement Seal Violation`).

## Enforcement Behavior

Implemented in `uniguru/enforcement/enforcement.py`:

- VERIFIED -> `ALLOW` and response prefixed with:
  - `Based on verified source: [source]`
- PARTIAL -> `ALLOW_WITH_DISCLAIMER` and response prefixed with:
  - `This information is partially verified from: [source]`
- UNVERIFIED -> `REFUSE` and response replaced with:
  - `I cannot verify this information from current knowledge.`

## Test Proof

Executed: `python -m pytest -q tests`

Included assertions in `tests/test_phase_requirements.py`:
- Signature present on response
- Tampering/invalid seal is blocked
- UNVERIFIED response is refused with exact required text

Result: `8 passed`
