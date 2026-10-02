# Execution Flow

Sprint: TANTRA Ecosystem Participation

---

## Full request path

```
1. User sends query
   └─ POST /runtime/ecosystem/execute  {query: "..."}

2. UniGuru — Kosha deterministic pipeline
   └─ run_deterministic_pipeline(query, trace_id, user_id)
      ├─ Retrieval (FAISS + Kosha)
      ├─ Constitutional semantic memory
      └─ Returns: pipeline_result {verification_status, answer, confidence, ...}

3. Vijay Validation (local constitutional hash)
   └─ _build_vijay_validation(trace_id, pipeline_result)
      ├─ ConstitutionalCognitionRuntime.execute(...)
      └─ Returns: {runtime_hash, replay_safe, last_event_hash, hash_chain_ok}

4. Bucket Telemetry
   └─ _build_bucket_telemetry(trace_id, pipeline_result)
      ├─ Writes local proof JSON
      └─ BucketTelemetryClient.emit(TelemetryEvent)  →  [LIVE when enabled]

5. TANTRA Contract
   └─ _build_tantra_contract(trace_id, pipeline_result, bucket_payload)
      └─ Returns: {schema, contract_bound, downstream_consumable, trace_continuity}

6. InsightFlow Observability
   └─ _build_insightflow_observability(trace_id, pipeline_result, vijay_validation)
      ├─ InsightFlowClient.emit_trace(...)   →  [LIVE when enabled]
      └─ InsightFlowClient.emit_decision(...)  →  [LIVE when enabled]

7. GC Validation
   └─ _build_gc_validation(vijay_validation, pipeline_result)
      ├─ GCClient.validate_authority(...)      →  [LIVE when enabled]
      └─ GCClient.validate_hidden_state(...)   →  [LIVE when enabled]

8. MDU Validation
   └─ _build_mdu_validation(trace_id, pipeline_result, vijay_validation)
      ├─ Builds evidence_payload conforming to runtime_evidence_contract.json
      ├─ MDUClient.validate_schema(evidence_payload)    →  [LIVE when enabled]
      └─ MDUClient.validate_provenance(lineage_payload) →  [LIVE when enabled]

9. TANTRA SDK Contracts
   └─ _build_tantra_sdk_contracts(trace_id, pipeline_result, query)
      ├─ TantraSdkAdapter.emit_execution_event(...)
      ├─ TantraRuntimeClient.submit_execution_event(...)  →  [LIVE when enabled]
      ├─ TantraRuntimeClient.submit_trace(...)            →  [LIVE when enabled]
      └─ TantraRuntimeClient.validate_authority(...)      →  [LIVE when enabled]

10. Proof emission
    ├─ Writes ecosystem_execution_{trace_id}.json
    └─ Writes ecosystem_execution_latest.json

11. Response returned to caller
    └─ {trace_id, answer, verification_status, vijay_validation, tantra_contract,
        bucket_telemetry, insightflow_observability, gc_validation, mdu_validation,
        tantra_sdk_contracts, execution_hash}
```

---

## Replay path

```
POST /runtime/ecosystem/replay  {query: "..."}
  └─ verify_ecosystem_replay()
     ├─ execute_ecosystem_runtime(query, trace_id=X)  →  first
     ├─ execute_ecosystem_runtime(query, trace_id=X)  →  replay
     └─ Checks:
        ├─ trace_id_stable
        ├─ vijay_runtime_hash_stable
        ├─ vijay_last_event_hash_stable
        ├─ tantra_contract_schema_stable
        ├─ tantra_trace_continuity_stable
        ├─ gc_authority_enforcement_stable
        └─ mdu_lineage_hash_stable
```

---

## Mitra path

```
POST /mitra/ecosystem/ask  {query: "..."}
  └─ execute_ecosystem_runtime()
     └─ Returns redacted payload:
        {trace_id, answer, verification_status, confidence, decision,
         replay_safe, contract_schema, downstream_consumable,
         observability_state, evidence}
```
