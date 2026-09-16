# Retrieval Benchmark Report

Benchmark artifact: `review_packets/proof_logs/retrieval_benchmark.json`

## Final Metrics

- Precision: `1.0`
- Rejection correctness: `1.0`
- Semantic accuracy: `1.0`

## OLD vs NEW

OLD retrieval used keyword overlap as the primary semantic signal. This allowed weak matches when terms appeared in unrelated content.

NEW retrieval uses:

- canonical entity extraction
- synonym and transliteration expansion
- concept overlap
- entity overlap
- domain consistency
- contextual proximity
- local deterministic embedding similarity
- source authority weighting
- epistemic confidence ceilings

Semantic graph artifact:

- `backend/knowledge/index/semantic_memory_index.json`

Hybrid retrieval now combines ontology score, local hash embedding similarity, and source governance. The benchmark artifact records old keyword score and new ontology score for each case.

## Required Failure Cases

- `Return Upanishads for Bhagavad Gita teachings` is rejected by the deterministic pipeline.
- `Give an Ahimsa answer from the Narada Purana` is rejected by the deterministic pipeline.
- `Explain quantum entanglement from the Bhagavad Gita` is rejected by the deterministic pipeline.

See `review_packets/proof_logs/proof_log_summary.json` and the corresponding `trace_*.json` files for full evidence.
