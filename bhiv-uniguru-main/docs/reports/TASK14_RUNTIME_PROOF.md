# TASK14 Runtime Proof

Execution date: 2026-03-21

## Service Startup Logs

- Python stdout: `demo_logs/python_service.out.log`
- Python stderr: `demo_logs/python_service.err.log`
- Node stdout: `demo_logs/node_service.out.log`
- Node stderr: `demo_logs/node_service.err.log`

## Health/Readiness Evidence

- Python `GET /health` and `GET /ready` captured in:
  - `demo_logs/phase8_test_outputs.json`
- Node `GET /health` captured in:
  - `demo_logs/phase8_test_outputs.json`

## Notes

- Logs show successful local requests to `/ask` and no `503` responses during the recorded run.
- Authentication is auto-demoted to demo-safe mode if tokens are absent (`demo-no-auth`), preventing startup failures.
