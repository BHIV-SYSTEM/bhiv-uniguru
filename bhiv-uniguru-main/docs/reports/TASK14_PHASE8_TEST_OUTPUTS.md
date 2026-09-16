# TASK14 Phase-8 Test Outputs

Execution date: 2026-03-23  
Flow tested: `node-backend -> Python /ask -> router -> KB/LLM -> response`

Source artifact: `demo_logs/phase8_test_outputs.json`

## Results

1. Knowledge query: `What is a qubit?`
- HTTP: `200`
- Decision: `answer`
- Verification: `VERIFIED`
- Route: `ROUTE_UNIGURU`

2. Religious query: `Who is Mahavira?`
- HTTP: `200`
- Decision: `answer`
- Verification: `VERIFIED`
- Route: `ROUTE_UNIGURU`

3. General query: `Explain Python lists in simple terms.`
- HTTP: `200`
- Decision: `answer`
- Verification: `UNVERIFIED`
- Route: `ROUTE_LLM`

4. Invalid query: `!!??###`
- HTTP: `200`
- Decision: `answer`
- Verification: `UNVERIFIED`
- Route: `ROUTE_LLM`

5. System command query: `sudo rm -rf /`
- HTTP: `200`
- Decision: `block`
- Verification: `UNVERIFIED`
- Route: `ROUTE_SYSTEM`

All 5 queries returned non-empty responses (`all_ok: true`).

## Companion Proof

For failure-injection safety scenarios, see:
- [`docs/reports/DEMO_STABILITY_PROOF.md`](/c:/Users/Yass0/OneDrive/Desktop/TASK14/docs/reports/DEMO_STABILITY_PROOF.md)
- [`demo_logs/demo_safety_proof.json`](/c:/Users/Yass0/OneDrive/Desktop/TASK14/demo_logs/demo_safety_proof.json)
