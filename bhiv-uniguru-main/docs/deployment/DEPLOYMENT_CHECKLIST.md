# UniGuru Deployment Readiness Checklist

This checklist tracks the transition of UniGuru into a live production system within the BHIV ecosystem.

## 1. System Audit
- [x] Review `service/api.py`
- [x] Review `live_service.py`
- [x] Review `API_SPEC.md`
- [x] Confirm endpoints: `/ask`, `/health`, `/ready`, `/metrics`, `/monitoring/dashboard`

## 2. API Authentication (Day 1)
- [x] Implement/Harden API token authentication in `service/api.py`.
- [x] Ensure `Authorization: Bearer` is supported.
- [x] Ensure 401 Unauthorized is returned for missing/invalid tokens.
- [x] Use `UNIGURU_API_TOKEN` environment variable.
- [x] Ensure no hardcoded credentials.

## 3. Service Access Control
- [x] Add explicit caller identification validation.
- [x] Allow `bhiv-assistant`, `gurukul-platform`, `internal-testing`.
- [x] Reject unknown callers with 403 Forbidden.

## 4. Reverse Proxy Setup
- [x] Prepare NGINX configuration for `uni-guru.in`.
- [x] Implement rate limit protection.
- [x] Configure request logging and header forwarding.

## 5. Production Deployment Configuration
- [x] Create `docker-compose.yml` for production.
- [x] Prepare startup script with `uvicorn`.
- [x] Configure worker scaling.

## 6. Domain, TLS & Integration
- [x] Configure `uni-guru.in` domain in NGINX virtual host.
- [x] Setup HTTPS/TLS certificate automation scripts (`deploy/certbot/*`).
- [x] Integrate UniGuru with BHIV Assistant request contract and caller controls.

## 7. Validation & Launch
- [x] Run cross-system integration tests.
- [x] Produce `PRODUCTION_DEPLOYMENT_REPORT.md`.
- [x] Produce `INTEGRATION_TEST_REPORT.md`.
- [x] Produce `LAUNCH_VALIDATION_REPORT.md`.
