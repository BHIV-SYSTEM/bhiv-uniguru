# Reviewer Notes — Sanskrit Knowledge Enrichment Engine (Phases 1–6)

## Purpose of the Code Packet

This code packet contains the core files modified and created for the **UniGuru Sanskrit Knowledge Enrichment Engine (Phases 1–6)**.

## Core Component Responsibilities & Interconnections

### 1. `sanskrit_decoder.py` — Canonical Engine (`v3`)
- **Location**: `backend/ontology/sanskrit_decoder.py`
- **Key Functions**:
  - `decode_sanskrit_concept(query)`: Main entry point. Resolves query against registry, executes Kosha multi-source retrieval, builds 35-layer civilizational knowledge object, constructs knowledge graph, attaches lineage provenance, and enforces zero-synthesis governance.
  - `_panini_sutra_lookup(dhatu_text, lexical)`: Looks up Pāṇini Ashtadhyayi sūtras in `grammar.md` for the given dhātu.
  - `_acoustic_phonetics(beeja_text, concept_name)`: Looks up Śikṣā acoustic metadata in `bija_phonetics.json`.
  - `_hermeneutics(sections, lexical)`: Parses `traditional_interpretations` into a 35th layer Darśana matrix.
  - `traverse_concept_graph(...)`: Performs BFS multi-hop traversal of the civilizational graph up to depth 6, maintaining provenance on every edge and path frame.

### 2. `uniguru_runtime_api.py` — Fast API Endpoints
- **Location**: `backend/service/uniguru_runtime_api.py`
- **Endpoints**:
  - `POST /runtime/sanskrit/decode` & `POST /v2/runtime/sanskrit/decode`: Decodes query into 35-layer civilizational object and graph.
  - `POST /v2/runtime/sanskrit/graph/traverse`: Accepts `start`, `edge_types`, `max_depth` to execute multi-hop graph traversal.

### 3. `grammar.md` & `bija_phonetics.json` — Vedāṅga Sources
- **Locations**: `backend/knowledge/gurukul/sanskrit/grammar.md` and `backend/knowledge/sanskrit/phonetics/bija_phonetics.json`.
- **Purpose**: Provide machine-readable Pāṇini Ashtadhyayi sūtras and Śikṣā acoustic phonetics for zero-synthesis enrichment.

### 4. `test_sanskrit_decoder.py` — Test Verification Suite
- **Location**: `backend/tests/test_sanskrit_decoder.py`
- **Coverage**: 9 unit tests verifying 23 concepts, 35 knowledge layers, Pāṇini sūtras, Śikṣā phonetics, comparative hermeneutics, multi-hop traversal, and `/v2` endpoints.

## Verification Checklist for Reviewers

- Run `pytest -q` in `backend/` -> verify **33 passed** (100%).
- Check `review_packets/proof_logs/sanskrit_graph_traverse_proof_prana_v3.json` -> verify **Prāṇa → Kosha → Chakra → Bīja** multi-hop traversal proof.
- Check `review_packets/proof_logs/sanskrit_decoder_proof_dharma_v2.json` -> verify 35-layer object structure.
