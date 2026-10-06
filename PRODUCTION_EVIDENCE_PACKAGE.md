# UniGuru Buyer Evidence Package

**Status:** NOT READY — live verification and independent witnesses are outstanding.
**Repository HEAD:** `6f58ca0` (remediation changes are uncommitted workspace changes).
**Prepared:** 2026-10-06

This package is an evidence index, not a production certification. Repository code and historical artifacts do not establish that a current deployment works.

## Current evidence status

| Acceptance area | Status | Evidence needed to close |
|---|---|---|
| Real user access | LIVE VERIFICATION REQUIRED | Production URL, auth result, browser journey, visible answer |
| End-to-end customer workflow | PARTIAL — automated workflow tests pass; LIVE VERIFICATION REQUIRED | Input, execution, output, durable record, provenance/trace, final user outcome |
| Failure, retry, auth, real data | PARTIAL — automated tests pass; LIVE VERIFICATION REQUIRED | See test results; complete deployed failure/auth/data exercise |
| Customer B deployment | CONFIGURED, NOT VERIFIED | Clean deployment from same commit/configured capability with customer boundaries |
| Buyer evidence and governance | PEER WITNESS REQUIRED | Current screenshots/video, evidence index, limitations/status, two BHIV witnesses |

## Repository configuration references

- API deployment: `render.yaml`
- Frontend API target: `frontend/.env.production`
- Frontend deployment procedure: `frontend/DEPLOYMENT.md`
- Backend runtime and API: `backend/service/api.py`
- Chat persistence: `backend/service/chat_storage.py`
- Chat acceptance tests: `backend/tests/test_chat_acceptance_security.py`

These files describe intended configuration and implementation. They are not proof of a currently live deployment.

## Automated verification performed 2026-10-06

- Backend suite: 294 passed, 1 skipped. The skipped test requires a FAISS index that is not committed.
- Focused auth, ownership, persistence, and chat workflow tests on the final edited code: 12 passed.
- Frontend production build (`npm.cmd run build`): passed. Vite reported existing bundle-size, mixed static/dynamic import, and stale Browserslist-data warnings.
- Python bytecode compilation and YAML parsing for Render/Compose: passed.
- These are repository/workspace checks. No deployed browser journey, provider-backed auth, service restart on a persistent Render disk, Customer B deployment, or peer witnessing was performed.

## Historical artifacts (not current acceptance evidence)

The repository contains dated activation logs, test summaries, benchmarks, and screenshots under `docs/reports/` and `review_packets/`. Preserve their original dates and local/deployment context when citing them. Do not represent them as current production verification.

## Live test record — complete during witnessed deployment test

- System / capability:
- Version / commit:
- Environment / deployment URL:
- Date and timezone:
- Peer 1:
- Peer 2:
- Q1 result and evidence:
- Q2 result and evidence:
- Q3 result and evidence:
- Q4 result and evidence:
- Q5 result and evidence:
- Screenshots/video:
- Trace/request IDs and provenance:
- Limitations / open gaps:
- Next three actions:
- Final verdict: NOT READY / READY FOR LIVE VERIFICATION / READY FOR PEER WITNESS / ACCEPTED

Do not use ACCEPTED unless all five questions have been demonstrated and two independent BHIV peers have witnessed the evidence.
