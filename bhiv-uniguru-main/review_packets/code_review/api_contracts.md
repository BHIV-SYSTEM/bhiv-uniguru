# API Contracts — Code Review Guide

**Owner:** Isha Singh

---

## 1. POST `/v2/runtime/sanskrit/decode`

### Request Payload:
```json
{
  "query": "dharma",
  "emit_proof": false
}
```

### Response Payload:
```json
{
  "trace_id": "sanskrit_a1b2c3d4e5f67890",
  "decoder_result": {
    "canonical_concept": {
      "concept_id": "sanskar:sanskrit:dharma",
      "canonical_name": "dharma",
      "sanskrit": "धर्म",
      "transliteration": "dharma",
      "functional_meaning": "Cosmic order, righteousness, law, and duty..."
    },
    "pipeline": [
      { "stage": "śabda", "value": "dh-r-m-a" },
      { "stage": "dhātu", "value": "dhṛ (to hold, sustain)" }
    ],
    "provenance": {
      "replay_safe": true,
      "source_documents": []
    }
  },
  "schema_version": "UNIGURU_SANSKRIT_DECODER_RESPONSE_V1",
  "response_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

---

## 2. POST `/v2/runtime/sanskrit/graph/traverse`

### Request Payload:
```json
{
  "start": "dharma",
  "max_depth": 3
}
```

### Response Payload:
```json
{
  "trace_id": "graph_traverse_12345",
  "traversal_result": {
    "start": "dharma",
    "max_depth": 3,
    "sub_graph": {
      "nodes": [],
      "edges": [],
      "node_count": 8,
      "edge_count": 7
    }
  },
  "schema_version": "UNIGURU_GRAPH_TRAVERSAL_RESPONSE_V1",
  "replay_safe": true
}
```

---

## 3. GET `/v2/convergence/authority_map`

### Response Payload:
```json
{
  "MASTERDB": { "authority_tier": "CANONICAL", "is_queried": true },
  "FAISS_VECTOR_INDEX": { "authority_tier": "DERIVED", "rebuildable": true },
  "LLM_FALLBACK": { "authority_tier": "FALLBACK", "is_queried": false }
}
```
