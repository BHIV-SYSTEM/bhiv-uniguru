# Replay Validation Report — Sanskrit Knowledge Decoder (Phases 1–6)

## Deterministic Replay Guarantee

The UniGuru Sanskrit Knowledge Enrichment Engine guarantees deterministic execution and replay safety. Given identical input queries, the decoder produces bit-level identical outputs, cryptographic hashes, and knowledge graph structures (`result_hash == replay_hash`).

## Hash Stability Verification

Across consecutive executions of `decode_sanskrit_concept()` and `traverse_concept_graph()`:
1. `result_hash`: Generated via `stable_hash(result)`. Replay stability verified (`result["result_hash"] == replay["result_hash"]`).
2. `response_hash`: Generated at API endpoint layer (`/runtime/sanskrit/decode`, `/v2/runtime/sanskrit/decode`, `/v2/runtime/sanskrit/graph/traverse`).
3. `graph_id`: `UNIGURU_CIVILIZATIONAL_KNOWLEDGE_GRAPH_V3`.
4. `source_snapshot_hash`: Matches cryptographic content hash of canonical markdown file.

## Cross-Service Ecosystem Replay Test

The TANTRA runtime ecosystem replay verification suite executes `verify_ecosystem_replay()`:
- **Test Target**: `dharma` (Trace ID: `test_sanskrit_dharma` / `isha_phase2_dharma_execution`)
- **Vijay Replay Safe**: `True`
- **Hash Chain OK**: `True`
- **Sanskrit Decoder Result Stable**: `True`
- **MDU Lineage Hash Stable**: `True`

## Automated Test Results

- `test_sanskrit_decoder.py::test_sanskar_source_retrieval_supports_all_supplied_concepts`: PASSED
- `test_sanskrit_decoder.py::test_graph_traversal_multi_hop_returns_provenance_chain`: PASSED
- `test_sanskrit_decoder.py::test_graph_traverse_endpoint_validates_depth_and_returns_path`: PASSED
- `test_sanskrit_ecosystem_integration.py::test_sanskrit_decoder_uses_existing_ecosystem_bucket_insightflow_and_replay`: PASSED

## Evidence Artifacts

- `review_packets/proof_logs/sanskrit_graph_traverse_proof_prana_v3.json`
- `review_packets/integration_proof/replay_verification_isha_sanskrit_dharma_v2.json`
- `review_packets/integration_proof/ecosystem_execution_isha_sanskrit_dharma_v2.json`
