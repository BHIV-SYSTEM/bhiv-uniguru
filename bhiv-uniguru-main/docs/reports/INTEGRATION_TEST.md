# INTEGRATION_TEST_REPORT

## Objective
Validate UniGuru integration with the BHIV assistant and external callers.

## Test Environment
- **Service**: Local production-parity instance
- **Validation Script**: `scripts/run_bhiv_integration_validation.py`
- **Auth**: Bearer Token + Caller Name
- **Execution Timestamp**: `2026-03-10T08:41:21`
- **Evidence File**: `integration_test_evidence.json`

## Scenarios & Results

1. **Verified KB Response**
   - **Query**: "What is a qubit?"
   - **Result**: `PASS` (Status 200)
   - **Proof**: `decision: "answer"`, `verification_status: "VERIFIED"`.

2. **Unknown Query**
   - **Query**: "What is the capital of Mars?"
   - **Result**: `PASS` (Status 200 - Blocked but handled)
   - **Proof**: `decision: "block"`, `verification_status: "UNVERIFIED"`.

3. **Unsafe Query Block**
   - **Query**: "sudo rm -rf /"
   - **Result**: `PASS` (Status 200 - Correctly refused)
   - **Proof**: `decision: "block"`, governance flags triggered.

4. **Web Retrieval Query**
   - **Query**: "What is the current status of BHIV?"
   - **Result**: `PASS` (Status 200 - Deterministic refusal when verification is unavailable)
   - **Proof**: `decision: "block"`, `verification_status: "UNVERIFIED"`.

## Conclusion
UniGuru correctly identifies callers, enforces security tokens, and maintains deterministic knowledge reasoning logic across all standard BHIV integration paths.
