# Integration Summary — Sanskrit Decoder Sprint

## What is integrated

### Sanskrit Decoder → UniGuru Pipeline
- `decode_sanskrit_concept()` is called inside `execute_ecosystem_runtime()` via `_attach_sanskrit_decoder()`
- When a Sanskrit concept is matched, the decoder output replaces the generic pipeline answer
- Domain is set to `"sanskrit"`, confidence to `0.65`, verification_status to `PARTIAL_VERIFIED_SAMPLE`

### Sanskrit Decoder UI → Runtime API
- Frontend React component `SanskritDecoder.tsx` calls `/v2/runtime/sanskrit/decode` via `sanskritDecoderApi.ts`
- SVG Knowledge Graph component `SanskritDecoderGraph.tsx` renders force-directed multi-node graphs from `/v2/runtime/sanskrit/graph/traverse`
- Route `/sanskrit-decoder` registered in `App.tsx` and accessible via LeftSidebar and ToolsPage
- Exposes 8-stage pipeline, 35 knowledge layers, evidence classification, Pāṇini sūtras, Śikṣā phonetics, and replay safety status to end users

### Sanskrit Decoder → TANTRA Contract
- `execution_event.v1.0.0` payload is built by `TantraSdkAdapter` and includes the Sanskrit domain
- `result_hash` from the decoder is included in `pipeline_summary.sanskrit_decoder`
- `sanskrit_decoder_result_stable` is one of the 8 replay verification checks

### Sanskrit Decoder → InsightCore + InsightBridge
- Every ecosystem execution calls `TantraEcosystemFabric.process_uniguru_event()`
- JWT is obtained from InsightCore `POST /auth/issue` (cached 55 min)
- Telemetry is posted to InsightBridge `POST /ingest` with trace_id in metadata

### Sanskrit Decoder → Bucket
- Local proof file written to `review_packets/integration_proof/bucket_{trace_id}.json`
- Live emit via `BucketTelemetryClient.emit()` when `UNIGURU_BUCKET_TELEMETRY_ENDPOINT` is set

### Sanskrit Decoder → InsightFlow
- `_build_insightflow_observability()` emits trace + decision to `/telemetry/ingest`
- Token: `flow_secret_789` (from Vijay's sovereign stack config)
- Blocked: `INSIGHTFLOW_BASE_URL` not set — Vijay's service is localhost-only

### Sanskrit Decoder → GC
- `_build_gc_validation()` submits authority + hidden-state validation
- Blocked: `GC_BASE_URL` not set

### Sanskrit Decoder → MDU
- `_build_mdu_validation()` validates schema + provenance against `BHIV-DS-UNIGURU-RUNTIME-001`
- Blocked: `MDU_API_KEY` not set

## Integration that is NOT done

| Integration | Reason |
|---|---|
| PRANA trust verification | No deployed endpoint from Vijay |
| KARMA capability consumption | No deployed endpoint from Vijay |
| Sanskrit domain in `snapshot_v1.json` | Sanskar has not delivered this |
| Live Bucket persistence | Bucket team has not provided endpoint |
| Live MDU validation | MDU team has not provided API key |
