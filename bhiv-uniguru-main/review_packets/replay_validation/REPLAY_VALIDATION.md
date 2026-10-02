# Replay Validation — Phase 2 Civilizational Knowledge Enrichment

## Determinism Guarantee

The decoder is deterministic. Given the same query and the same corpus, it always produces the same output.

### Determinism Sources

1. **File loading**: `sorted(SOURCE_DIR.glob("*.md"))` — alphabetical order, deterministic
2. **Registry**: `SanskritRegistry` stores concepts in a sorted dict — deterministic iteration
3. **Resolution**: `_resolve()` returns `None` if more than one match — no ambiguity
4. **Kosha retrieval**: `sorted(KOSHA_DIR.glob("*.json"))` — alphabetical order; records sorted by `(-score, knowledge_id, path)` — deterministic
5. **Graph construction**: nodes and edges built in deterministic order; nodes deduplicated by id
6. **Result hash**: `stable_hash(result)` — SHA-256 of the JSON-serialized result

### Replay Check Fields

The `verify_ecosystem_replay()` function in `ecosystem_runtime.py` checks these fields:
1. `result_hash` — must match exactly
2. `canonical_concept.concept_id` — must match
3. `canonical_concept.canonical_name` — must match
4. `provenance.registry_version` — must match
5. `provenance.schema_version` — must match
6. `provenance.lineage.content_hash` — must match (source file unchanged)
7. `governed_response.research_classification` — must match
8. `governed_response.governance_state` — must match

---

## Replay Test Protocol

To verify replay consistency:

```python
from ontology.sanskrit_decoder import decode_sanskrit_concept

# Run 1
result1 = decode_sanskrit_concept("dharma")
hash1 = result1["result_hash"]

# Run 2 (same process, same corpus)
result2 = decode_sanskrit_concept("dharma")
hash2 = result2["result_hash"]

assert hash1 == hash2, "Replay failed — non-deterministic output"
```

This test passes as long as:
- The source `.md` files have not changed
- The Kosha files have not changed
- The Python environment is the same

---

## What Breaks Replay (Expected)

| Change | Effect on Replay |
|--------|-----------------|
| Editing a source `.md` file | `content_hash` changes → `result_hash` changes → replay fails (expected — source changed) |
| Adding a new Kosha record | `records_found` changes → `result_hash` changes → replay fails (expected — corpus changed) |
| Changing `DECODER_VERSION` | `semantic_version` changes → `result_hash` changes → replay fails (expected — version changed) |
| Running on different OS | No effect — `stable_hash` uses SHA-256 which is platform-independent |
| Running at different time | No effect — no timestamps in the deterministic output |

---

## Unknown Concept Handling

When a query does not match any registered concept:

```json
{
  "canonical_concept": null,
  "civilizational_knowledge": null,
  "governed_response": {
    "evidence_classification": {
      "classification": "UNVERIFIED",
      "notes": "No source-backed Sanskrit lexical record matched this query."
    },
    "research_classification": "UNVERIFIED",
    "governance_state": "no_inference"
  },
  "result_hash": "<hash of this null result>"
}
```

The null result is also deterministic — the same unknown query always produces the same `result_hash`.

---

## Performance Metrics

| Operation | Expected Time |
|-----------|--------------|
| `load_sanskar_registry()` (20 files) | < 100ms |
| `_kosha_records()` (37 files) | < 500ms |
| `decode_sanskrit_concept("dharma")` end-to-end | < 1 second |
| `decode_sanskrit_concept("unknown")` | < 200ms |

These are estimates based on local file I/O. Actual performance depends on disk speed.
