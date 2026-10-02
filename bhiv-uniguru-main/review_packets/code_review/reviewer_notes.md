# Reviewer Notes — Sanskrit Decoder Sprint

## What reviewers need to know

### 1. The decoder is NOT a translation engine
It does not call any LLM to decode Sanskrit. It reads Sanskar's immutable `.md` source documents and exposes the structured knowledge layers directly. The `result_hash` is deterministic — the same query always produces the same hash.

### 2. The registry bootstrap is solved
Previous audit noted "no registry bootstrap loader" as a gap. Isha solved this in `load_sanskar_registry()` — it reads all `.md` files from `backend/knowledge/sanskrit/`, parses them via `_section_map()`, and registers them into `SanskritRegistry` at call time. No separate bootstrap script is needed.

### 3. The runtime API is now mounted
`uniguru_runtime_api.py` was previously a standalone FastAPI app not reachable from the deployed backend. It is now mounted under `/v2` in `main.py`. All routes are reachable at `https://uniguru-ai-2.onrender.com/v2/...`.

### 4. Live ecosystem services — honest status
InsightCore and InsightBridge are live and wired. All other services (InsightFlow, PRANA, KARMA, GC, MDU) are either not deployed by Vijay or missing credentials. The integration clients are fully implemented and will activate automatically when endpoints are provided. This is not a code gap — it is a deployment gap on Vijay's side.

### 5. Proof files are real
Every execution writes a deterministic proof file to `review_packets/integration_proof/` and `review_packets/proof_logs/`. These are not mocked — they are the actual output of `run_deterministic_pipeline()` and `execute_ecosystem_runtime()`.

### 6. What to verify independently
- Run `pytest backend/tests/test_sanskrit_decoder.py` — should pass with zero external dependencies
- Run `pytest backend/tests/test_sanskrit_ecosystem_integration.py` — should pass locally
- Launch frontend `npm run dev` and navigate to `/sanskrit-decoder` (or click Sanskrit Decoder under Tools menu)
- Enter "dharma", "karma", or "prana" — verify 8-stage pipeline, 35 knowledge layers, SVG knowledge graph, Pāṇini sūtras, and replay safety badge
- Hit `GET https://uniguru-ai-2.onrender.com/health/ecosystem` — shows InsightCore live status
- Hit `POST https://uniguru-ai-2.onrender.com/v2/runtime/sanskrit/decode` with `{"query": "dharma"}` — returns full 8-stage decoder output

### 7. What is genuinely incomplete
- PRANA and KARMA: zero integration — Vijay has not deployed these services
- MDU: client is complete but `MDU_API_KEY` is empty — MDU team has not provided the key
- Bucket live telemetry: endpoint not configured — Bucket team has not provided the URL
- Sanskrit domain node in `snapshot_v1.json`: missing — Sanskar has not delivered this
