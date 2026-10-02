# Next Tasks — UniGuru Sanskrit Knowledge Engine

## Current State (Post Phase 1–6 + Typed Node Traversal)

- 23 canonical Sanskrit concepts with 35-layer civilizational knowledge objects
- Recursive typed-node BFS traversal: `sanskrit_concept → kosha → chakra → bija → ...`
- Pāṇini Ashtadhyayi sūtra catalogue + Śikṣā acoustic phonetics
- Comparative Hermeneutics (8 Darśana traditions)
- 34/34 tests passing

---

## Phase 7 — Corpus Expansion

- [ ] Expand from 23 to 50+ canonical Sanskrit concepts
- [ ] Add missing concepts: Nāda, Bindu, Spanda, Turīya, Mahat, Ahaṃkāra, Buddhi, Citta, Manas, Apāna, Samāna, Udāna, Vyāna, Pañcabhūta
- [ ] Complete `experimental_hypotheses` sections with source-backed hypotheses from UniGuru research
- [ ] Expand `historical_evolution` sections with archaeological and textual evidence

## Phase 7A — Typed Node Registry

- [ ] Create a `TypedNodeRegistry` (separate from `SanskritRegistry`) to register canonical Kosha, Chakra, Bīja, Mantra, Vidyā, Śāstra, Yantra, Loka, and Deity entries with their own source-backed records
- [ ] Load typed node records from structured markdown/JSON files in `backend/knowledge/typed_nodes/`
- [ ] Enable cross-typed-node traversal with source-backed edge discovery (not hardcoded mapping)

## Phase 8 — Query Layer Enhancements

- [ ] Add fuzzy Devanagari/IAST matching to resolver
- [ ] Support compound query resolution (e.g., "Prāṇamaya Kosha" → `kosha_ref:pranamaya_kosha`)
- [ ] Implement reverse traversal: `Yaṃ Bīja → Anāhata Chakra → Prāṇamaya Kosha → Prāṇa`
- [ ] Add path filtering by `evidence_type` (e.g., VEDA only, UPANISHAD only)

## Phase 9 — Knowledge Graph Explorer API

- [ ] Build `GET /v2/runtime/sanskrit/graph/neighborhood/{node_id}` — return immediate neighbors of any typed node
- [ ] Build `GET /v2/runtime/sanskrit/graph/paths?from={a}&to={b}` — find all paths between two nodes
- [ ] Build `GET /v2/runtime/sanskrit/graph/stats` — return graph-level statistics (node types, edge types, coverage)

## Phase 10 — Conversational Retrieval Integration

- [ ] Wire `traverse_concept_graph()` into UniGuru conversational retrieval pipeline
- [ ] Expose Knowledge Graph Explorer results as context in conversational responses
- [ ] Implement TANTRA-aware retrieval routing for Sanskrit concept queries

## Phase 11 — Performance & Caching

- [ ] Cache `load_sanskar_registry()` result at process startup
- [ ] Cache `_load_grammar_catalogue()` and `_load_phonetics_map()` results
- [ ] Benchmark decode latency at 1000 RPS and optimize
