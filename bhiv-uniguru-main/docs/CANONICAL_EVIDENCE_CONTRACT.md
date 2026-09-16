# Canonical Evidence Contract Specification

**Version:** 1.0.0  
**Owner:** Isha Singh  
**MDU Governance ID:** `MDU-CANONICAL-EVIDENCE-V1`

---

## 1. Purpose & Authority Boundary

This contract specifies the schema and validation constraints for retrievable evidence objects used by UniGuru.

### Governance Boundaries:
- **TMS**: Knowledge Strategy
- **GC**: Governance Policy & Safety Sealing
- **MDU**: Schema, Identifiers & Provenance Authority
- **Isha**: Runtime Contract Enforcement

No retrievable candidate may enter the LLM or reasoning synthesis phase without satisfying the `CanonicalKnowledgeObject` schema.

---

## 2. Canonical Knowledge Object Schema

```json
{
  "$schema": "https://uniguru.ai/schemas/v1/canonical_knowledge_object.json",
  "type": "object",
  "required": [
    "canonical_object_id",
    "concept_id",
    "ksml_id",
    "source_id",
    "authority_tier",
    "tradition_context",
    "text_span",
    "provenance_hash",
    "schema_version",
    "knowledge_version"
  ],
  "properties": {
    "canonical_object_id": {
      "type": "string",
      "pattern": "^uko:[a-z0-9_]+:[a-f0-9]{12}$",
      "description": "Immutable URI identifier for the knowledge object."
    },
    "concept_id": {
      "type": "string",
      "description": "Clean canonical concept identifier."
    },
    "ksml_id": {
      "type": "string",
      "description": "KSML semantic concept identity tag."
    },
    "source_id": {
      "type": "string",
      "description": "Source identifier (e.g. MASTERDB, AKASHIC, KOSHA)."
    },
    "authority_tier": {
      "type": "string",
      "enum": ["CANONICAL", "DERIVED", "FALLBACK", "TEST_FIXTURE", "LEGACY"]
    },
    "tradition_context": {
      "type": "string",
      "description": "School / Darśana / domain context (e.g. advaita, dvaita, mimamsa, general)."
    },
    "text_span": {
      "type": "string",
      "description": "Verbatim clean text span extracted from source."
    },
    "provenance_hash": {
      "type": "string",
      "pattern": "^[a-f0-9]{64}$",
      "description": "SHA-256 hash of object identity and content span."
    },
    "schema_version": {
      "type": "string",
      "default": "UNIGURU_CANONICAL_OBJECT_V1"
    },
    "knowledge_version": {
      "type": "string",
      "default": "1.0.0"
    },
    "parent_derived_relations": {
      "type": "array",
      "items": { "type": "string" }
    },
    "graph_relations": {
      "type": "array",
      "items": { "type": "string" }
    }
  }
}
```

---

## 3. Retrieval Run Record Schema

Every query execution produces a `RetrievalRunRecord` documenting candidate counts, deduplication results, and selected evidence items.

```json
{
  "query_id": "query_ade4cecc234e",
  "trace_id": "trace_bf93f080a7e462b6",
  "canonical_concept_id": "dharma",
  "semantic_scope": "general",
  "retrieval_run_id": "run_2535f9dc1e47",
  "index_version": "UNIGURU_CONVERGENCE_INDEX_V1",
  "candidate_count": 3,
  "deduplicated_candidate_count": 2,
  "selected_evidence": [
    {
      "canonical_object_id": "uko:dharma:006f7b061f4c",
      "source_id": "MASTERDB",
      "authority_tier": "CANONICAL",
      "provenance_hash": "006f7b061f4c65c17f171e3b7c0669b82b8879a86150dc22b968243a7d014e21",
      "ranking_score": 0.85,
      "dedup_status": "unique",
      "text_span": "Dharma is the sustaining order of life and duty."
    }
  ],
  "claim_bindings": [
    {
      "claim_id": "claim_1_b921477f",
      "claim_text": "Dharma is the sustaining order of life and duty.",
      "canonical_object_id": "uko:dharma:006f7b061f4c",
      "source_id": "MASTERDB",
      "text_span": "Dharma is the sustaining order of life and duty.",
      "verification_status": "VERIFIED",
      "confidence": 0.85,
      "provenance_hash": "006f7b061f4c65c17f171e3b7c0669b82b8879a86150dc22b968243a7d014e21"
    }
  ],
  "verification_status": "VERIFIED",
  "replay_id": "replay_05407b21fb826372",
  "replay_safe": true
}
```
