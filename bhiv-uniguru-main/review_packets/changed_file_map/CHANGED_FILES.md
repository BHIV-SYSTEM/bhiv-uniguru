# Changed Files Map — Sanskrit Knowledge Enrichment Engine (Phases 1–6)

## Overview of Changed & Created Files

The repository changed files are organized by component responsibility:

### 1. Core Ontology Engine & Data Map

- [`backend/ontology/sanskrit_decoder.py`](file:///c:/Users/Isha%20Singh/Desktop/uniguru%203/uniguru/backend/ontology/sanskrit_decoder.py)
  - **Responsibility**: Core 35-layer Civilizational Knowledge Engine (`v3`), alias resolution, multi-source retrieval, Pāṇini sūtra lookup, Śikṣā acoustic phonetics lookup, comparative hermeneutics matrix parser, zero-synthesis claim builder, knowledge graph construction, and `traverse_concept_graph()` BFS multi-hop traversal function.

- [`backend/knowledge/gurukul/sanskrit/grammar.md`](file:///c:/Users/Isha%20Singh/Desktop/uniguru%203/uniguru/backend/knowledge/gurukul/sanskrit/grammar.md)
  - **Responsibility**: Gurukul Vedāṅga grammar source file expanded with a machine-readable JSON catalogue of Pāṇini Ashtadhyayi sūtras for all 23 concept roots.

- [`backend/knowledge/sanskrit/phonetics/bija_phonetics.json`](file:///c:/Users/Isha%20Singh/Desktop/uniguru%203/uniguru/backend/knowledge/sanskrit/phonetics/bija_phonetics.json) [NEW]
  - **Responsibility**: Machine-readable bīja seed syllable acoustic phonetics map sourced to Vedic Śikṣā texts (*Pāṇinīya-Śikṣā*, *Taittirīya Prātiśākhya*).

- [`backend/knowledge/sanskrit/lokas.md`](file:///c:/Users/Isha%20Singh/Desktop/uniguru%203/uniguru/backend/knowledge/sanskrit/lokas.md) [NEW]
  - **Responsibility**: Canonical markdown record for Lokas (Seven higher/lower cosmic planes).

- [`backend/knowledge/sanskrit/koshas.md`](file:///c:/Users/Isha%20Singh/Desktop/uniguru%203/uniguru/backend/knowledge/sanskrit/koshas.md) [NEW]
  - **Responsibility**: Canonical markdown record for Koshas (Five sheaths of human embodiment).

- [`backend/knowledge/sanskrit/chakras.md`](file:///c:/Users/Isha%20Singh/Desktop/uniguru%203/uniguru/backend/knowledge/sanskrit/chakras.md) [NEW]
  - **Responsibility**: Canonical markdown record for Chakras (Six subtle energy centers).

### 2. Service Endpoints & Ecosystem Integration

- [`backend/service/uniguru_runtime_api.py`](file:///c:/Users/Isha%20Singh/Desktop/uniguru%203/uniguru/backend/service/uniguru_runtime_api.py)
  - **Responsibility**: FastAPI production service layer exposing `/runtime/sanskrit/decode`, `/v2/runtime/sanskrit/decode`, and `/v2/runtime/sanskrit/graph/traverse` endpoints.

- [`backend/integrations/mdu_client.py`](file:///c:/Users/Isha%20Singh/Desktop/uniguru%203/uniguru/backend/integrations/mdu_client.py)
  - **Responsibility**: MDU Intelligence Data Universe client with `BHIV-DS-UNIGURU-RUNTIME-001` integration.

### 3. Test Suite & Proof Generators

- [`backend/tests/test_sanskrit_decoder.py`](file:///c:/Users/Isha%20Singh/Desktop/uniguru%203/uniguru/backend/tests/test_sanskrit_decoder.py)
  - **Responsibility**: Test suite covering 23 concepts, 35 knowledge layers, Pāṇini sūtras, Śikṣā phonetics, comparative hermeneutics, multi-hop graph traversal, `/v2` endpoints, and unknown concept safety.

- [`scripts/generate_phase2_proof_logs.py`](file:///c:/Users/Isha%20Singh/Desktop/uniguru%203/uniguru/scripts/generate_phase2_proof_logs.py)
  - **Responsibility**: Script generating machine-readable JSON proof logs for all 23 concept decodes, graph traversal proof (`Prāṇa → Kosha → Chakra → Bīja`), and ecosystem execution/replay proofs.
