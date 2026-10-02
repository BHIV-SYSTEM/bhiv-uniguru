# Architecture Map — Code Review Guide

**Owner:** Isha Singh  
**Purpose:** Enable reviewers to understand the architecture without traversing the codebase.

---

## 1. System Component Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                  │
│  SanskritDecoder.tsx ──> SanskritDecoderGraph.tsx ──> sanskritDecoderApi│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP POST /v2/runtime/sanskrit/decode
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                             SERVICE API                                │
│                     uniguru_runtime_api.py                             │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
                  ▼                                   ▼
┌───────────────────────────────────┐   ┌────────────────────────────────┐
│      SANSKRIT DECODER ENGINE      │   │    KNOWLEDGE CONVERGENCE       │
│      sanskrit_decoder.py          │   │    convergence_runtime.py      │
│  - 8-stage pipeline               │   │  - Candidate Deduplication     │
│  - 35 knowledge layers            │   │  - Authority Contracts         │
│  - Pāṇini sūtra lookup            │   │  - Claim-to-Evidence Binding   │
│  - Śikṣā acoustic phonetics       │   │  - Replay ID Sealing           │
│  - Knowledge graph BFS            │   │  - Canonical Knowledge Objects │
└───────────────────────────────────┘   └────────────────────────────────┘
```

---

## 2. Component Inventory

| Component | Path | Responsibility |
|---|---|---|
| **Decoder Engine** | `backend/ontology/sanskrit_decoder.py` | Core 35-layer epistemological decoder engine |
| **Convergence Runtime** | `backend/convergence/convergence_runtime.py` | Candidate deduplication & claim-evidence binding |
| **Authority Contract** | `backend/convergence/authority_contract.py` | Authority tier registry (`CANONICAL`, `DERIVED`, `FALLBACK`) |
| **Canonical Object** | `backend/convergence/canonical_object.py` | MDU-compliant retrievable knowledge object schema |
| **Evidence Contract** | `backend/convergence/retrieval_evidence_contract.py` | `RetrievalRunRecord` & `ClaimEvidenceBinding` dataclasses |
| **Service Layer** | `backend/service/uniguru_runtime_api.py` | FastAPI runtime routes |
| **Frontend UI** | `frontend/src/components/SanskritDecoder.tsx` | React decoder interface |
| **Graph UI** | `frontend/src/components/SanskritDecoderGraph.tsx` | SVG force-directed Knowledge Graph component |
