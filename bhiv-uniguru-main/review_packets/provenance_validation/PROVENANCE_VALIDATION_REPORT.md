# Provenance Validation Report — Sanskrit Knowledge Decoder (Phases 1–6)

## Provenance Architecture

The UniGuru Sanskrit Knowledge Enrichment Engine enforces strict provenance tracking across all decoded concepts and multi-hop graph traversals. Provenance metadata is generated deterministically at decode/traversal time and attached to every claim, graph node, and edge.

## Lineage Protocol & Metadata

Every claim in the 35-layer civilizational knowledge object includes:
- `source_id`: 16-character SHA-256 hash derived from concept ID/source reference.
- `evidence_type`: Formally classified evidence category (`VEDA`, `UPANISHAD`, `BHAGAVAD_GITA`, `PRIMARY_CANON`, `PANINI`, `NIRUKTA`, `COMMENTARY`, `TRADITION`, `DERIVED`).
- `source_path`: Relative repository path to canonical source file (`knowledge/sanskrit/*.md`, `gurukul/sanskrit/grammar.md`, `phonetics/bija_phonetics.json`).
- `content_hash`: Cryptographic hash of the source document text.
- `retrieval_system`: `sanskrit_lexical_records`, `uniguru_kosha`, `uniguru_vedanga_grammar`, `uniguru_vedanga_shiksha`.

## Evidence Classification Rules

```python
if "gita" in token or "bhagavad" in token: -> EvidenceType.BHAGAVAD_GITA
if "upanishad" in token or "taittiriya" in token: -> EvidenceType.UPANISHAD
if "veda" in token or "rigveda" in token: -> EvidenceType.VEDA
if "panini" in token or "ashtadhyayi" in token: -> EvidenceType.PANINI
if "nirukta" in token or "yaska" in token: -> EvidenceType.NIRUKTA
if "bhasya" in token or "sankara" in token: -> EvidenceType.COMMENTARY
if "siksha" in token or "pratisakhya" in token: -> EvidenceType.VEDA (VEDANGA_SHIKSHA)
```

## MDU Intelligence Data Universe Integration

- **Canonical Dataset ID**: `BHIV-DS-UNIGURU-RUNTIME-001`
- **Replay Events Dataset ID**: `BHIV-DS-REPLAY-SEMANTIC-EVENTS-001`
- **Lineage Chain Dataset ID**: `BHIV-DS-LINEAGE-CHAIN-001`
- **Schema Compatibility**: Verified live/mocked via `MDUClient.validate_schema()` and `MDUClient.validate_provenance()`.

## Audit & Verification Logs

Machine-readable proof logs validating lineage preservation across executions:
- `review_packets/proof_logs/sanskrit_decoder_proof_dharma_v2.json`
- `review_packets/proof_logs/sanskrit_decoder_proof_lokas_v2.json`
- `review_packets/proof_logs/sanskrit_decoder_proof_koshas_v2.json`
- `review_packets/proof_logs/sanskrit_decoder_proof_chakras_v2.json`
- `review_packets/proof_logs/sanskrit_graph_traverse_proof_prana_v3.json`
