# SELF VALIDATION — Native Sanskrit Knowledge Decoder
**Owner:** Isha Singh
**Sprint:** Sanskrit Knowledge Decoder (Sprint 3)

---

## Sprint 3 — Sanskrit Decoder

**Does UniGuru execute the canonical decoder pipeline when a Sanskrit concept is queried?**
YES. `decode_sanskrit_concept()` in `backend/ontology/sanskrit_decoder.py` executes all 8 stages: śabda → dhātu → vyākaraṇa → nirukta → bīja → tattva → śakti → functional_meaning. Verified by `test_sanskrit_decoder.py`.

**Are all Sanskrit source documents loaded and parsed correctly?**
YES. `load_sanskar_registry()` loads 23 concept records + Lokas + Koshas + Chakras from `backend/knowledge/sanskrit/*.md`, Pāṇini sūtras from `grammar.md`, and Śikṣā phonetics from `bija_phonetics.json`.

**Is every layer exposed deterministically?**
YES. The same query produces the same `result_hash` on every execution. Verified by replay test: `result_hash` of `decode_sanskrit_concept("dharma")` equals `decode_sanskrit_concept("धर्म")`.

**Is every conclusion traceable?**
YES. Every pipeline stage includes `lineage` with `concept_id`, `source_path`, and `content_hash`.

**Is every statement evidence-classified?**
YES. `EvidenceType` enum classifies each source (BHAGAVAD_GITA, UPANISHAD, PANINI, VEDA, NIRUKTA, COMMENTARY, PRIMARY_CANON, TRADITION). Classification is derived from source documents and maps, not inferred.

**Does the knowledge graph exist and support multi-hop traversal?**
YES. `_graph()` and `traverse_concept_graph()` build and walk nodes and edges (concepts, koshas, chakras, bija, lokas, deities, shastras). Graph consistency is validated — edges reference only registered nodes.

**Is every execution replay-safe?**
YES. `result_hash` is deterministic. `verify_ecosystem_replay()` confirms `sanskrit_decoder_result_stable: true`.

**Is every output provenance-backed?**
YES. `Provenance` dataclass includes `trace_id`, `content_hash`, and `source_path`.

**Is the decoder integrated into UniGuru end-to-end with a user interface?**
YES. `POST /v2/runtime/sanskrit/decode` and `/v2/runtime/sanskrit/graph/traverse` endpoints are live. React UI component `SanskritDecoder.tsx`, SVG graph renderer `SanskritDecoderGraph.tsx`, API client `sanskritDecoderApi.ts`, route `/sanskrit-decoder`, and navigation entries in `LeftSidebar.tsx` and `ToolsPage.tsx` provide a full native user experience.

---

## Sprint 1 — Live TANTRA Integration

**Are all local ecosystem integrations replaced by live services?**
PARTIAL. InsightCore JWT and InsightBridge ingest are wired with live HTTP clients. InsightFlow, PRANA, KARMA, GC are wired but not live — Vijay's services are not deployed.

**Does every request traverse the canonical TANTRA runtime?**
NO. PRANA and KARMA have no deployed endpoints. InsightFlow has no deployed URL.

**Are Trace IDs preserved across every service?**
YES locally. The same `trace_id` flows through pipeline → bucket → InsightFlow → GC → MDU → TANTRA contract. Live cross-service verification is blocked.

**Can Replay reconstruct execution end-to-end?**
YES locally. `verify_ecosystem_replay()` passes all 8 deterministic checks. Live Bucket reconstruction is blocked — Bucket endpoint not configured.

**Does Bucket persist authenticated runtime evidence?**
PARTIAL. Local proof files are written to `review_packets/integration_proof/`. Live Bucket endpoint is not configured — `UNIGURU_BUCKET_TELEMETRY_ENDPOINT` is empty.

**Does InsightFlow receive complete execution telemetry?**
NO. `INSIGHTFLOW_BASE_URL` is not set — Vijay's InsightFlow is localhost-only, not deployed.

**Do GC and MDU validate every execution?**
NO. `GC_BASE_URL` is not set. `MDU_API_KEY` is empty.

**Can Vijay independently reproduce the same execution?**
NOT VERIFIED. Vijay has not confirmed joint execution.

**Can the entire execution be replayed without hidden state?**
YES. All execution state is deterministic and written to proof files. No hidden local state.

**Is every production claim backed by evidence?**
YES for Sanskrit Decoder. NO for live ecosystem services — no live service has confirmed receipt.

---

## Blockers Summary

| Service | Status | Blocker Owner |
|---|---|---|
| InsightCore JWT | WIRED — not live-verified | Render cold start |
| InsightBridge ingest | WIRED — not live-verified | Depends on JWT |
| InsightFlow | WIRED — not live | Vijay (not deployed) |
| PRANA | NOT WIRED — no endpoint | Vijay (not deployed) |
| KARMA | NOT WIRED — no endpoint | Vijay (not deployed) |
| GC | WIRED — not live | GC team (no endpoint) |
| MDU | WIRED — not live | MDU team (no API key) |
| Bucket | WIRED — not live | Bucket team (no endpoint) |
