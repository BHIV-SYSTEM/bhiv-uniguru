# Training Readiness

## How Curriculum Data Becomes Governed Cognition Substrate

Balbharti content enters MasterDB as structured curriculum records, not raw PDF blobs. Each record carries grade, medium, subject, chapter, concept, definition, examples, questions, language variant, curriculum version, and source lineage.

The runtime treats each record as a governed knowledge unit. Retrieval can select it, interpretation can explain it, but constitutional governance decides how much trust and authority the answer may carry. Sample-seed records are useful for execution proof, but they do not become canonical authority until source verification is complete.

## Replay-Safe Knowledge Lineage

The ingestion script builds a deterministic manifest over normalized records:

- record hash per curriculum unit
- dataset hash across the sample set
- manifest hash across ingestion state
- replay proof copied to `review_packets/proof_logs/balbharti_masterdb_ingestion_proof.json`

Runtime answers include source lineage and emit a replay artifact under `review_packets/proof_logs/uniguru_runtime_execution_latest.json`. This means later review can reconstruct which curriculum record shaped the answer, what trust ceiling was applied, and whether contradiction or ontology alerts were present.

## Token Accounting Framework

Training preparation should account for tokens at the curriculum-unit level:

- record metadata tokens: grade, medium, subject, chapter, source lineage
- concept tokens: concept, definition, examples, questions
- governance tokens: provenance status, review state, replay hash references
- multilingual alignment tokens: language variant and concept-pair mapping

No training batch should drop provenance fields to save tokens. Compression is allowed only after hashes and source references remain recoverable.

## Curriculum Chunking Discipline

Chunks should follow stable educational boundaries:

- one concept per chunk where possible
- examples and questions stay attached to their concept
- medium-specific wording remains separate
- cross-medium alignment is represented as metadata, not merged text
- chapter and grade boundaries are retained

## Multilingual Grounding Strategy

Marathi and English records are both first-class. The system may align equivalent concepts, but it must preserve the original language variant and source lineage. Translation is an interpretation layer, not a replacement for curriculum text.

## Indic Grounding Without Unbounded Authority

Indian civilizational semantic tagging can be introduced as bounded metadata: local examples, language families, regional terms, and educational context. It must not convert cultural familiarity into truth authority.

Controls:

- provenance remains mandatory
- sample seeds remain non-canonical
- contradictions between editions, translations, or cultural explanations stay visible
- ontology boundaries cap legitimacy even when confidence is high
- review packets record what is verified, simulated, and unresolved
