# BHIV Assistant Integration Report

Date: 2026-03-12

## Implemented Integration
- BHIV Assistant request contract enforced in `/ask`:
  - `caller` accepted from `context.caller` (preferred) or `X-Caller-Name`.
  - `session_id` accepted and propagated to router/service logs.
  - `allow_web` accepted and propagated into routing context.
- Route metadata captured and returned in response:
  - `routing.query_type`
  - `routing.route`
  - `routing.router_latency_ms`
- Structured log event confirms route metadata and caller/session fields:
  - event: `request_processed`
  - keys: `caller_name`, `session_id`, `query_hash`, `route`, `verification_status`

## Evidence
- Ecosystem validation script: `scripts/run_ecosystem_validation.py`
- Evidence JSON: `demo_logs/ecosystem_validation_report.json`
- Raw execution log: `demo_logs/ecosystem_validation.log`

Validated scenarios:
1. BHIV Assistant knowledge query -> `ROUTE_UNIGURU`
2. Gurukul knowledge query -> `ROUTE_UNIGURU`
3. Workflow request -> `ROUTE_WORKFLOW`
4. System command -> `ROUTE_SYSTEM` with block decision

All four scenarios returned HTTP 200 in local validation and deterministic routing outcomes.
