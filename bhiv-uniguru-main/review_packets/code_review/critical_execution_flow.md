# Critical Execution Flow — Code Review Guide

**Owner:** Isha Singh

---

## 1. Primary Request Execution Path

```text
1. Request Ingestion
   POST /v2/runtime/sanskrit/decode {"query": "dharma"}
   └─> uniguru_runtime_api.py: runtime_sanskrit_decode()

2. Concept Resolution
   decode_sanskrit_concept("dharma")
   └─> sanskrit_decoder.py: _resolve()
       └─> load_sanskar_registry() -> matches "sanskar:sanskrit:dharma"

3. Pipeline Construction
   └─> sanskrit_decoder.py: 8 pipeline stages
       [śabda, dhātu, vyākaraṇa, nirukta, bīja, tattva, śakti, functional_meaning]

4. Knowledge Enrichment
   └─> _panini_sutra_lookup() -> grammar.md
   └─> _acoustic_phonetics() -> bija_phonetics.json
   └─> _darshana_matrix() -> comparative hermeneutics

5. Knowledge Graph Traversal
   └─> _graph() -> builds nodes & directed edges

6. Provenance & Replay Sealing
   └─> stable_hash(payload) -> result_hash & trace_id

7. Response Rendering
   └─> React UI: SanskritDecoder.tsx rendering 8 stages + 35 layers + SVG graph
```
