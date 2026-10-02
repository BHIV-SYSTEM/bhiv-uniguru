# Changed File Map

Sprint: TANTRA Ecosystem Participation

## New Files

| File | Purpose |
|------|---------|
| `backend/integrations/tantra_runtime_client.py` | Live HTTP client for Vijay TANTRA SDK — Runtime, Replay, Trace, Authority, Capability contracts |
| `backend/integrations/insightflow_client.py` | Live HTTP client for InsightFlow — traces, decisions, metrics, failures |
| `backend/integrations/gc_client.py` | Live HTTP client for GC — authority, hidden-state, governance-drift |
| `backend/integrations/mdu_client.py` | Live HTTP client for MDU — schema, provenance, replay-lineage |

## Modified Files

| File | Change Summary |
|------|---------------|
| `backend/integrations/__init__.py` | Added exports for `GCClient`, `InsightFlowClient`, `MDUClient`, `TantraRuntimeClient` |
| `backend/service/ecosystem_runtime.py` | Wired all four new live clients into `_build_insightflow_observability`, `_build_gc_validation`, `_build_mdu_validation`, `_build_tantra_sdk_contracts`; added live response fields to each layer's output |
| `backend/.env.example` | Added env vars for TANTRA SDK, InsightFlow, GC, MDU, Bucket, Core Reader |
| `review_packets/REVIEW_PACKET.md` | Replaced fabricated evidence with accurate integration state |
| `review_packets/execution_summary.md` | Replaced fabricated evidence with accurate sprint summary |
| `review_packets/code_review/changed_file_map.md` | This file |
| `review_packets/code_review/critical_code_packets.md` | Critical path code review |
| `review_packets/code_review/reviewer_notes.md` | Reviewer guidance |
| `review_packets/code_review/dependency_graph.md` | Dependency graph |

## Unchanged Files (relevant to integration)

| File | Reason unchanged |
|------|-----------------|
| `backend/integrations/bucket_telemetry.py` | Already had live HTTP emission; no changes needed |
| `backend/integrations/tantra_sdk_adapter.py` | Payload builder; still used to construct events before submission |
| `backend/service/uniguru_runtime_api.py` | API surface unchanged; ecosystem_runtime.py handles integration |
| `backend/governance/constitutional_runtime.py` | Governance logic unchanged; no bypass |
| `backend/contracts/runtime_evidence_contract.json` | Schema unchanged; MDU validates against it |
