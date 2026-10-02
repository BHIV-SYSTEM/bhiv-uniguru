# REVIEW PACKET — Native Sanskrit Knowledge Decoder
**Sprint:** Sanskrit Knowledge Decoder (Sprint 3)
**Owner:** Isha Singh — UniGuru Runtime Owner
**Date:** 2026
**Status:** COMPLETE (local) | PARTIAL (live ecosystem — blocked by Vijay deployment)

---

## What This Sprint Delivers

A native Sanskrit Knowledge Decoder built into UniGuru that decodes Sanskrit concepts through their own epistemology — not translation, not dictionary lookup, not RAG. Every concept is decoded through 8 canonical layers and 35 civilizational knowledge layers sourced from Sanskar's immutable knowledge documents, with a complete native React UI, SVG knowledge graph, and deterministic runtime backend API.

---

## Canonical Execution Pipeline & User Experience

```
User Query (Frontend Input or API)
    ↓
POST /v2/runtime/sanskrit/decode  [uniguru_runtime_api.py]
    ↓
decode_sanskrit_concept()  [ontology/sanskrit_decoder.py]
    ↓
load_sanskar_registry()  — loads 23 concept records + Lokas + Koshas + Chakras
    ↓
_resolve()  — matches query (Devanagari, IAST, or transliteration) to canonical concept
    ↓
8-Stage Pipeline:
  śabda → dhātu → vyākaraṇa → nirukta → bīja → tattva → śakti → functional_meaning
    ↓
35 Knowledge Layers:
  Pāṇini sūtras + Śikṣā acoustic phonetics + Darśana matrix + scientific & ritual domains
    ↓
_graph() + traverse_concept_graph() — builds & walks multi-hop Knowledge Graph
    ↓
_provenance()  — evidence classification per source (SOURCE_SCOPED, DERIVED, EXPERIMENTAL)
    ↓
stable_hash(result)  — deterministic result_hash + replay_safe verification
    ↓
React Frontend Component  [components/SanskritDecoder.tsx + SanskritDecoderGraph.tsx]
```

---

## Supported Capabilities & Concepts

- **Concepts**: 23 canonical concepts (Dharma, Karma, Prana, Atman, Brahman, Shakti, Yajna, Om, Kala, Akasha, Guru, Vidya, Samskara, Maya, Prakrti, Purusha, Rta, Moksha, Yoga, Lokas, Koshas, Chakras, Yantras)
- **UI Route**: `/sanskrit-decoder` (accessible via LeftSidebar and ToolsPage)
- **Interactive Knowledge Graph**: SVG force-directed node graph with hover tooltips and edge classification
- **Evidence Badging**: Source-scoped vs. derived vs. experimental classification on every claim
- **Replay Safety**: Explicit replay-safe verification badge on every output

---

## Critical Files

1. `backend/ontology/sanskrit_decoder.py` — full 35-layer decoder implementation & graph traversal
2. `backend/service/uniguru_runtime_api.py` — API endpoints `POST /v2/runtime/sanskrit/decode` and `/v2/runtime/sanskrit/graph/traverse`
3. `frontend/src/components/SanskritDecoder.tsx` — main Sanskrit Knowledge Decoder UI component
4. `frontend/src/components/SanskritDecoderGraph.tsx` — SVG force-directed Knowledge Graph component
5. `frontend/src/routes/SanskritDecoderPage.tsx` — route page wrapper for `/sanskrit-decoder`

---

## Evidence

- Proof logs: `review_packets/proof_logs/isha_sanskrit_dharma_v1.json`
- Ecosystem execution: `review_packets/integration_proof/ecosystem_execution_isha_sanskrit_dharma_v1.json`
- Replay verification: `review_packets/integration_proof/replay_verification_isha_sanskrit_dharma_v1.json`
- Bucket proof: `review_packets/integration_proof/bucket_isha_sanskrit_dharma_v1.json`
- Test suite: `backend/tests/test_sanskrit_decoder.py`, `backend/tests/test_sanskrit_ecosystem_integration.py`

---

## Blockers (not Isha's lane)

| Blocker | Owner | Impact |
|---|---|---|
| InsightFlow not deployed | Vijay | `live_emitted: false` for InsightFlow |
| PRANA not deployed | Vijay | No PRANA trust verification |
| KARMA not deployed | Vijay | No KARMA capability consumption |
| GC endpoint missing | GC team | `live: false` for governance validation |
| MDU_API_KEY missing | MDU team | `live: false` for schema/provenance validation |

All integration clients are wired and will activate automatically when endpoints are provided.
