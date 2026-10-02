# UniGuru Live Test Logs

Date: 2026-03-19

Source log files:
- `demo_logs/uniguru_live_activation_logs.json`
- `docs/reports/UNIGURU_LIVE_ACTIVATION_LOGS.json`

## Product Chat Query

- Endpoint: `POST /api/v1/chat/query`
- Input query: `What is a qubit?`
- HTTP status: `200`
- Routing: `ROUTE_UNIGURU`
- Verification status: `VERIFIED`
- Request ID: `f8bd164d-55c5-45b2-87c8-5508f9ed027d`

## Gurukul Student Query

- Endpoint: `POST /api/v1/gurukul/query`
- Input query: `Explain the Pythagorean theorem.`
- Student ID: `STU-1001`
- HTTP status: `200`
- Routing: `ROUTE_UNIGURU`
- Verification status: `UNVERIFIED`
- Status action: `REFUSE`
- Request ID: `dd39bba0-9404-4292-b056-a2c9ef184f30`

## Full Activation Matrix

Scenarios executed:
1. Gurukul student query
2. Product chat query
3. Knowledge query
4. Unsafe query
5. General chat query

Result: `all_passed = true`

Data quality check:
- `SSSS` response artifact removed from source KB and regenerated activation logs.
