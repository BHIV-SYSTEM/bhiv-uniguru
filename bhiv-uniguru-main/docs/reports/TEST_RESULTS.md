# FULL_REASONING_TEST_RESULTS

## Test Execution
Command:
- `PYTHONPATH=. pytest -q tests/ontology_reasoning_test.py`

Result:
- `6 passed`

## Deterministic Reasoning Traces
Snapshot:
- version: `1`
- hash: `e7292c6b78cfa8c7fe0008b36f6916879af5b9c78d763a3cbf402d3e3d6895ad`

### 1) Quantum Query
Query:
- `What is a qubit?`

Reasoning trace:
```json
{
  "concept_chain": ["quantum root", "qubit"],
  "truth_levels": [4, 3],
  "snapshot_version": 1,
  "snapshot_hash": "e7292c6b78cfa8c7fe0008b36f6916879af5b9c78d763a3cbf402d3e3d6895ad"
}
```

### 2) Jain Query
Query:
- `Explain ahimsa in jainism`

Reasoning trace:
```json
{
  "concept_chain": ["jain root", "ahimsa"],
  "truth_levels": [4, 3],
  "snapshot_version": 1,
  "snapshot_hash": "e7292c6b78cfa8c7fe0008b36f6916879af5b9c78d763a3cbf402d3e3d6895ad"
}
```

### 3) Swaminarayan Query
Query:
- `What is vachanamrut in swaminarayan tradition?`

Reasoning trace:
```json
{
  "concept_chain": ["swaminarayan root", "vachanamrut"],
  "truth_levels": [4, 3],
  "snapshot_version": 1,
  "snapshot_hash": "e7292c6b78cfa8c7fe0008b36f6916879af5b9c78d763a3cbf402d3e3d6895ad"
}
```


## Merged: ECOSYSTEM_ROUTING_TESTS.md

# Ecosystem Routing Tests

## Covered Scenarios
1. Knowledge query
- Input: `What is a qubit?`
- Expected route: `ROUTE_UNIGURU`

2. Conversation query
- Input: `hello there`
- Expected route: `ROUTE_LLM`

3. Unsafe query
- Input: `sudo delete all files`
- Expected route: `ROUTE_SYSTEM`
- Expected decision: `block`

4. Workflow query
- Input: `create workflow ticket for access request`
- Expected route: `ROUTE_WORKFLOW`

5. System command
- Input: `shutdown system now`
- Expected route: `ROUTE_SYSTEM`
- Expected decision: `block`

## Automated Test Files
- `tests/test_conversation_router.py`
- `tests/test_registry_api.py` (router integration cases)

## Execution Command
```powershell
pytest tests/test_conversation_router.py tests/test_registry_api.py -q
```

## Evidence
- Integration logs: `demo_logs/router_integration.log`
- Routing test output: `demo_logs/routing_test_output.txt`

## Result Criteria
- All scenario tests pass.
- `/ask` response contains `routing.query_type` and `routing.route`.
- Queue guard rejects excess load with `503`.
- Metrics include route counters and queue rejection counter.


## Merged: LIVE_TRUTH_TEST_RESULTS.md

# LIVE_TRUTH_TEST_RESULTS

## Objective 
Prove UniGuru refuses unverifiable knowledge.

## Test Categories and Results

| Category | Input | Output Prefix | Verification Status | Verdict |
|----------|-------|---------------|---------------------|---------|
| Verified Question | "Who is Rishabhadeva?" | `Based on verified source: rishabhadeva_adinatha.md` | `VERIFIED` | **SUCCESS** |
| Partially Verified | "Tell me about Guru info" | `This information is partially verified from: Production UniGuru backend` | `PARTIAL` | **SUCCESS** |
| Unverified Question | "What is the best pizza in New York?" | `Verification status: UNVERIFIED` | `UNVERIFIED` | **SUCCESS (REFUSED)** |
| Gurukul Integration | "Explain nyaya logic" | `Based on verified source: nyaya_logic.md` | `VERIFIED` | **SUCCESS** |

## Conclusion
The UniGuru Sovereign Language System successfully discriminates between its internal verified knowledge base and external/unverified queries. The system correctly refuses to answer out-of-scope/unverified questions while providing source-traceable answers for verified content. No hallucinations or guesses were detected during testing.
