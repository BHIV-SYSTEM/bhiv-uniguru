# Provenance Validation — Phase 2 Civilizational Knowledge Enrichment

## Provenance Architecture

Every claim in the decoder output carries provenance. There are three levels:

### Level 1 — Lexical Provenance (Source Document)
Every field from the `.md` source file carries:
```json
{
  "source_id": "<sha256[:16] of concept_id + source>",
  "evidence_type": "BHAGAVAD_GITA | UPANISHAD | VEDA | PRIMARY_CANON | TRADITION | ...",
  "provenance": {
    "source_text": "<canonical source name>",
    "chapter": "",
    "verse": "",
    "validation_status": "UNVERIFIED"
  },
  "source_path": "backend/knowledge/sanskrit/dharma.md",
  "content_hash": "<sha256 of raw file content>",
  "retrieval_system": "sanskrit_lexical_records"
}
```

### Level 2 — Kosha Provenance (Retrieved Records)
Every Kosha record retrieved carries:
```json
{
  "knowledge_id": "<kosha record id>",
  "provenance": {
    "source_path": "backend/data/kosha/KOSHA_xxx.json",
    "content_hash": "<sha256 of record>",
    "retrieval_system": "uniguru_kosha",
    "evidence_type": "TRADITION | PRIMARY_CANON | ..."
  }
}
```

### Level 3 — Result Hash (Replay Proof)
The entire result is hashed deterministically:
```python
result["result_hash"] = stable_hash(result)
```
The same query on the same corpus always produces the same `result_hash`.

---

## Evidence Type Classification

| Evidence Type | When Applied |
|--------------|-------------|
| `VEDA` | Source contains "veda", "rigveda", "atharvaveda" |
| `UPANISHAD` | Source contains "upanishad" or "upanisad" |
| `BHAGAVAD_GITA` | Source contains "gita" |
| `PRIMARY_CANON` | Source contains "sutra", "brahma sutra", "yoga sutra" |
| `PANINI` | Source contains "panini" or "ashtadhyayi" |
| `NIRUKTA` | Source contains "nirukta" or "yaska" |
| `COMMENTARY` | Source contains "bhasya", "commentary", "tika" |
| `TRADITION` | All other sources |
| `DERIVED` | Cross-references derived from the lexical record |

---

## Provenance Validation Checks

### Check 1 — Source Document Exists
Every concept's `source_path` points to an existing `.md` file.

| Concept | Source Path | Exists |
|---------|------------|--------|
| dharma | backend/knowledge/sanskrit/dharma.md | ✅ |
| karma | backend/knowledge/sanskrit/karma.md | ✅ |
| atman | backend/knowledge/sanskrit/atman.md | ✅ |
| brahman | backend/knowledge/sanskrit/brahman.md | ✅ |
| moksha | backend/knowledge/sanskrit/moksha.md | ✅ |
| yoga | backend/knowledge/sanskrit/yoga.md | ✅ |
| agni | backend/knowledge/sanskrit/agni.md | ✅ |
| prana | backend/knowledge/sanskrit/prana.md | ✅ |
| om | backend/knowledge/sanskrit/om.md | ✅ |
| maya | backend/knowledge/sanskrit/maya.md | ✅ |
| shakti | backend/knowledge/sanskrit/shakti.md | ✅ |
| samskara | backend/knowledge/sanskrit/samskara.md | ✅ |
| guru | backend/knowledge/sanskrit/guru.md | ✅ |
| vidya | backend/knowledge/sanskrit/vidya.md | ✅ |
| yajna | backend/knowledge/sanskrit/yajna.md | ✅ |
| rta | backend/knowledge/sanskrit/rta.md | ✅ |
| akasha | backend/knowledge/sanskrit/akasha.md | ✅ |
| kala | backend/knowledge/sanskrit/kala.md | ✅ |
| prakrti | backend/knowledge/sanskrit/prakrti.md | ✅ |
| purusha | backend/knowledge/sanskrit/purusha.md | ✅ |

### Check 2 — Content Hash Stability
The `content_hash` is computed as `stable_hash(raw_file_content)`. It changes only when the source file changes. This ensures that any modification to the source is detectable.

### Check 3 — Experimental Hypotheses Marked
All experimental hypotheses in the source files are explicitly marked with `[EXPERIMENTAL — NOT CANONICAL]`. The decoder checks for this marker and sets `status: "EXPLICITLY_MARKED_EXPERIMENTAL"` rather than `"EVIDENCE_BACKED"`.

### Check 4 — No LLM-Generated Canonical Claims
All canonical claims in the source files are derived from named canonical sources (Ṛgveda, Upaniṣads, Bhagavad Gītā, etc.). No claim is presented as canonical without a named source.

### Check 5 — Graph Consistency
The `_graph()` function validates that all edge endpoints exist as nodes before returning. If any edge references a non-existent node, it raises `ValueError("Civilizational graph consistency validation failed")`.

---

## What Provenance Does NOT Cover (Honest)

1. **Chapter and verse numbers** — the `Provenance` dataclass has `chapter` and `verse` fields, but they are currently empty strings. The source files list canonical sources by name but not by specific verse. This is the next level of enrichment.

2. **Kosha record provenance depth** — Kosha records carry `source_path` and `content_hash` but not the original publication details of the source they were derived from.

3. **MDU provenance layer** — not connected (MDU_API_KEY missing).

4. **Validation status** — all provenance records have `validation_status: "UNVERIFIED"`. Independent verification against the original texts has not been performed programmatically.
