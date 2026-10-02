# Execution Flow — Native Sanskrit Knowledge Decoder

## Entry Point
`POST /v2/runtime/sanskrit/decode`
Request: `{ "query": "धर्म", "emit_proof": true }`

---

## File 1 — `backend/service/uniguru_runtime_api.py`

```
runtime_sanskrit_decode(request)
    ↓
decode_sanskrit_concept(request.query)
    ↓
trace_id = stable_hash(result_hash)[:16]
    ↓
payload = { trace_id, decoder_result, governed_response, replay, response_hash }
    ↓
write proof file → review_packets/proof_logs/sanskrit_decoder_{trace_id}.json
    ↓
return payload
```

---

## File 2 — `backend/ontology/sanskrit_decoder.py`

```
decode_sanskrit_concept(query)
    ↓
load_sanskar_registry()
    — reads backend/knowledge/sanskrit/*.md (6 files)
    — parses ## sections into SanskritConcept via sanskrit_concept_from_dict()
    — registers into SanskritRegistry (immutable)
    — computes content_hash per file via stable_hash()
    ↓
_resolve(query, registry)
    — normalises query (NFC, casefold)
    — matches against canonical_name, sanskrit, transliteration, ascii variants
    ↓
if no match → return UNVERIFIED result with result_hash
    ↓
_provenance(concept, metadata)
    — maps source names to EvidenceType enum values
    — builds provenance list with source_id hashes
    ↓
pipeline = 8 stages
    [ śabda, dhātu, vyākaraṇa, nirukta, bīja, tattva, śakti, functional_meaning ]
    each stage: { stage, schema_field, value, evidence, classification, lineage }
    ↓
_graph(concept, registry, metadata)
    — builds nodes for concept + all related_concepts found in registry
    — builds edges with EvidenceType.DERIVED
    — validates: all edge endpoints exist as nodes
    ↓
result = { canonical_concept, pipeline, cross_references, knowledge_graph,
           functional_meaning, provenance, governed_response }
result["result_hash"] = stable_hash(result)
    ↓
return result
```

---

## File 3 — `backend/service/ecosystem_runtime.py`

```
execute_ecosystem_runtime(query)
    ↓
run_deterministic_pipeline(query, trace_id)   [kosha pipeline]
    ↓
_attach_sanskrit_decoder(query, pipeline_result)
    — calls decode_sanskrit_concept(query)
    — if canonical_concept found: enriches pipeline_result with decoder output
    — sets answer = functional_meaning.summary
    — sets domain = "sanskrit"
    — sets confidence = 0.65
    ↓
_build_vijay_validation()     → runtime_hash, replay_safe, hash_chain_ok
_build_bucket_telemetry()     → local proof file + live emit (if configured)
_build_tantra_contract()      → schema, trace_continuity
_build_insightflow_observability() → trace_hash, live emit (if configured)
_build_gc_validation()        → authority_enforced, live validate (if configured)
_build_mdu_validation()       → schema_compatible, live validate (if configured)
_build_tantra_sdk_contracts() → execution_event.v1.0.0 payload
tantra_fabric.process_uniguru_event() → InsightCore JWT → InsightBridge /ingest
    ↓
execution_hash = stable_hash(deterministic_fields_only)
    ↓
write proof → review_packets/integration_proof/ecosystem_execution_{trace_id}.json
    ↓
return full payload
```

---

## Deterministic Fields (replay-stable)

```python
{
    "trace_id": trace_id,
    "query": query,
    "verification_status": ...,
    "confidence": ...,
    "answer": ...,
    "vijay_runtime_hash": ...,
    "vijay_last_event_hash": ...,
    "tantra_contract_schema": ...,
    "mdu_lineage_hash": ...,
    "gc_authority_enforced": ...,
    "tantra_fabric_status": ...,   # "ingested" or "ingest_failed"
    "prana_verified": ...,
}
```

Live service responses (InsightBridge response body, InsightFlow ack) are excluded from `execution_hash` so replay is stable regardless of live service availability.

---

## Replay Verification

`verify_ecosystem_replay(query, trace_id)` runs the pipeline twice with the same `trace_id` and checks 8 fields:

| Check | Field |
|---|---|
| trace_id_stable | trace_id |
| vijay_runtime_hash_stable | vijay_validation.runtime_hash |
| vijay_last_event_hash_stable | vijay_validation.last_event_hash |
| tantra_contract_schema_stable | tantra_contract.schema |
| tantra_trace_continuity_stable | tantra_contract.trace_continuity |
| gc_authority_enforcement_stable | gc_validation.authority_enforced |
| mdu_lineage_hash_stable | mdu_validation.evidence_payload.lineage_hash |
| sanskrit_decoder_result_stable | pipeline_summary.sanskrit_decoder.result_hash |
