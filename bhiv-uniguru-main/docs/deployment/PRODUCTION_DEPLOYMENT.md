# PRODUCTION_DEPLOYMENT_REPORT

## Deployment Overview
UniGuru is configured for secured, containerized deployment behind NGINX with token authentication, caller allowlisting, and observability endpoints.

## Infrastructure Stack
- OS/runtime: Python 3.12 + Uvicorn
- Service image: `Dockerfile` (`uvicorn uniguru.service.api:app`)
- Scaling: `UNIGURU_WORKERS` env-driven worker count
- Edge gateway: NGINX (`deploy/nginx/nginx.conf`, `deploy/nginx/conf.d/uniguru.conf`)
- TLS automation: Certbot renewal loop (`deploy/certbot/renew.sh`)

## Security and Access Control
- Bearer token enforced for `/ask`, `/metrics`, `/metrics/reset`, `/monitoring/dashboard`
- Token source: `UNIGURU_API_TOKEN` / `UNIGURU_API_TOKENS` env vars only
- Caller validation: `context.caller` or `X-Caller-Name` against `UNIGURU_ALLOWED_CALLERS`
- Unknown caller behavior: HTTP `403`
- Missing/invalid token behavior: HTTP `401`

## Observability and Stability
- `/health` and `/ready` available for probes
- Prometheus metrics at `/metrics` (authenticated)
- JSON monitoring summary at `/monitoring/dashboard` (authenticated)
- API middleware rate limiting and latency headers enabled

## Verification Evidence (Executed 2026-03-10)
- API/security test suite: `pytest -q tests/test_registry_api.py` -> `12 passed`
- Service stability evidence: `demo_logs/service_stability_evidence.json`
- Integration verification: `integration_test_evidence.json`

## Domain/TLS Note
Domain-level validation for `https://uni-guru.in/health` must be executed on BHIV production infrastructure after DNS and certificate issuance are completed. This workspace run validates production parity locally.
