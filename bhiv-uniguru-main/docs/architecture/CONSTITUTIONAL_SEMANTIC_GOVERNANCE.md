# Constitutional Semantic Governance

UniGuru semantic persistence is now mediated by an append-only governance layer.
The layer is designed for deterministic mutation decisions, observable lineage,
replay-safe reconstruction, contradiction auditability, and rollback previews.

## Boundary Rules

1. Interpretation never mutates retrieval truth.
2. Persistent semantic observations never become canonical without governance acceptance.
3. Canonical memory is reconstructed from append-only semantic events.
4. Contradictions are quarantined audit events, not silent merges.
5. Ontology references are carried as lineage and do not rewrite ontology snapshots.
6. Missing retrieval truth, missing interpretation hash, or bypassed boundary status blocks canonical authority.

## Runtime Flow

`Kosha retrieval -> retrieval truth hash -> bounded interpretation hash -> truth/interpretation link -> SemanticMemoryStore -> ConstitutionalSemanticMemory -> event log -> deterministic reconstruction -> checkpoint + observability`

The existing `SemanticMemoryStore` remains the pipeline facade, but canonical
authority now comes from `ConstitutionalSemanticMemory` governance decisions.

## Persistence Artifacts

- `review_packets/proof_logs/constitutional_semantic_events.jsonl`
  - Append-only mutation events.
  - Each event has a deterministic `mutation_id`, `event_hash`, and `previous_event_hash`.
- `review_packets/proof_logs/constitutional_semantic_checkpoint.json`
  - Replay reconstruction of canonical, transient, contradiction, and lineage state.
- `review_packets/proof_logs/constitutional_semantic_observability.json`
  - Telemetry summary for event count, canonical entity count, transient count, contradiction count, state hash, and hash-chain status.
- `review_packets/proof_logs/constitutional_semantic_proof.json`
  - Replay, contradiction, rollback, poisoning, corruption, and observability proof bundle.

## Acceptance Rules

Canonical memory requires:

- trace id
- retrieval truth hash
- interpretation hash
- enforced truth/interpretation boundary
- interpretation reference to retrieval truth
- `VERIFIED` status
- at least one accepted signal
- confidence at or above `0.55`
- no contradiction pressure and no contradiction list

Rejected observations are classified as `transient` or `quarantined`.
They remain observable and replayable, but they do not gain canonical authority.

## Replay And Rollback

Replay reads `constitutional_semantic_events.jsonl` in order, validates each
event hash, validates the previous-event hash chain, and reconstructs:

- canonical memory
- transient memory
- contradiction audit
- lineage continuity

Rollback preview reconstructs state until a target `event_hash` without editing
or deleting the event log.

## Testing

Run:

```powershell
python -m pytest backend\tests\test_constitutional_semantic_memory.py --basetemp .pytest_tmp
python scripts\run_constitutional_semantic_proof.py
```

The tests cover replay reconstruction, contradiction quarantine, poisoning
rejection, rollback preview, corruption detection, and ontology mutation drift.
