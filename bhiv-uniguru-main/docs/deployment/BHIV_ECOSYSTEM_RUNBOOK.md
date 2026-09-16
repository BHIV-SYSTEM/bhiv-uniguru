# BHIV Ecosystem Runbook

## Local Acceptance

```powershell
.venv\Scripts\python.exe -m pytest backend/tests/test_constitutional_runtime.py backend/tests/test_ecosystem_integration.py -q
.venv\Scripts\python.exe scripts\run_ecosystem_acceptance.py
```

## Runtime Launch

```powershell
$env:UNIGURU_API_AUTH_REQUIRED="false"
.venv\Scripts\python.exe -m uvicorn backend.service.uniguru_runtime_api:app --host 127.0.0.1 --port 8000
```

## Verification

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/ready
Invoke-RestMethod http://127.0.0.1:8000/metrics
Invoke-RestMethod http://127.0.0.1:8000/runtime/ecosystem/execute -Method Post -ContentType "application/json" -Body '{"query":"What is the Bhagavad Gita?","emit_proof":true}'
Invoke-RestMethod http://127.0.0.1:8000/runtime/ecosystem/replay -Method Post -ContentType "application/json" -Body '{"query":"What is the Bhagavad Gita?","emit_proof":true}'
Invoke-RestMethod http://127.0.0.1:8000/mitra/ecosystem/ask -Method Post -ContentType "application/json" -Body '{"query":"What is the Bhagavad Gita?","emit_proof":true}'
```

## Acceptance Gates

- Vijay replay validation: `replay_safe=true`
- TANTRA: `contract_bound=true` and `downstream_consumable=true`
- Bucket: telemetry proof written or remote emitter configured
- InsightFlow: `trace_complete=true`
- GC: `authority_enforced=true`
- MDU: `schema_compatible=true` and `provenance_continuity=true`
- Replay: `replay_verified=true`
- Mitra: response omits internal governance payloads
