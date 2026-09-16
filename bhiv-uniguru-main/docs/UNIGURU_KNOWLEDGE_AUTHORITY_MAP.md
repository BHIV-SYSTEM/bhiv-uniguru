# UniGuru Knowledge Authority Map

**Version:** 1.0.0  
**Owner:** Isha Singh (Knowledge Convergence & Trust Validation Layer)  
**Status:** Active Governance Specification  
**Authority Authority (MDU/GC/TMS Boundary):**
- **TMS**: Strategy & High-level Knowledge Policy
- **GC**: Operational Governance & Policy Enforcement
- **MDU**: Schema, Lineage & Provenance Authority
- **Isha**: Knowledge Convergence, Contract Enforcement & Claim Binding Runtime

---

## 1. Executive Summary & Runtime Reality Audit

The UniGuru platform previously contained multiple knowledge paths (`MASTERDB`, `AKASHIC`, `KNOWLEDGE_GRAPH`, `KOSHA_JSON`, `MARKDOWN_CORPUS`, `FAISS_VECTOR_INDEX`, `LLM_FALLBACK`). Without strict governance, vector retrieval and local fixtures risked acting as competing semantic authorities.

This document establishes the official **Knowledge Authority Hierarchy**. Vector indices (FAISS) are demoted to **Derived, Rebuildable Search Indexes**, while structured primary stores (`MASTERDB`, `AKASHIC`, `KSML Concepts`) serve as **Canonical Truth**.

---

## 2. Knowledge Source Classification Matrix

| Knowledge Source | Active Query Path | Authority Status | Contains Data | Influences Output | Provenance | Rebuild Path | Governance Owner |
|---|---|---|---|---|---|---|---|
| **MASTERDB** (`masterdb/balbharti/`) | YES | `CANONICAL` | Balbharti textbook curriculum, grade/subject metadata | YES | Source record ID, chapter lineage | Ground truth ingest pipeline | MDU / Isha |
| **AKASHIC** (`data/kosha/`) | YES | `CANONICAL` | Primary Kosha knowledge records, classical texts | YES | Knowledge ID, text hash, domain tag | Ingest & purification script | MDU / Isha |
| **KNOWLEDGE_GRAPH** (`ontology/`) | YES | `CANONICAL` | Entity relations, Darśana matrix, Pāṇini sūtras | YES | Graph node ID, edge classification | Ontology build & snapshot loader | Isha / Sanskar |
| **KOSHA_JSON** (`data/kosha/entries/`) | YES | `CANONICAL` | Validated Kosha entries | YES | Entry ID, source text span | Kosha Enforcer | Isha |
| **MARKDOWN_CORPUS** (`backend/knowledge/`) | YES | `CANONICAL` | Domain markdowns (Sanskrit, Quantum, Jain, etc.) | YES | Content hash, path | Knowledge ingest parser | Isha |
| **FAISS_VECTOR_INDEX** (`backend/retrieval/`) | YES | `DERIVED` | Dense embedding vectors for candidate search | YES (Candidate stage only) | Vector ID → Canonical Object ID | Rebuild script `scripts/rebuild_faiss_index.py` | Vijay (Search Engine) |
| **LLM_FALLBACK** (`service/api.py`) | CONDITIONAL | `FALLBACK` | Generative completion | ONLY when unverified fallback allowed | Explicit fallback tag + warning | N/A (generative) | Vijay / Isha |
| **TEST_FIXTURE** (`tests/fixtures/`) | TESTS ONLY | `TEST_FIXTURE` | Mock test payloads | NO (Excluded in production) | Fixture hash | Static code fixture | Isha |

---

## 3. Authority Tiers & Policy Rules

### A. Tiers Defined
1. `CANONICAL`: Immutable primary truth. Claims backed by canonical sources receive maximum trust ceilings (up to `1.0`).
2. `DERIVED`: Secondary search indices generated directly from canonical objects (e.g. FAISS vector tables, keyword inverted indices). Derived objects must map 1:1 back to a `canonical_object_id`. If a derived object loses its canonical backing, it MUST be invalidated.
3. `FALLBACK`: Safe fallback outputs used when no verified canonical evidence passes threshold. Fallbacks must explicitly set `verification_status: "NO_VERIFIED_KNOWLEDGE"` or `FALLBACK`.
4. `TEST_FIXTURE`: Mock data used strictly in test environments. Forbidden in production query runs.
5. `LEGACY`: Deprecated data schemas or obsolete Kosha entries. Quarantined from active retrieval.

---

## 4. Derived FAISS Index Remediation

### The Rule:
Vector embeddings (FAISS) are **retrieval accelerators**, not truth providers.

### Rebuild Specification:
1. **Trigger**: Any modification to `MASTERDB`, `AKASHIC`, or `backend/knowledge/`.
2. **Process**:
   - `scripts/rebuild_faiss_index.py` reads all `CANONICAL` objects.
   - Extracts clean text spans and generates embeddings via `EmbeddingProvider`.
   - Stores candidate metadata mapping `vector_id → canonical_object_id`.
3. **Validation**: Every vector candidate retrieved during query execution must be resolved back to its `canonical_object_id`. Unresolved vectors are discarded as index drift.

---

## 5. Traceability & Replay Guarantee

For every query processed by UniGuru, the runtime emits a `RetrievalRunRecord` containing:
- `query_id` and `trace_id`
- `retrieval_run_id` and `index_version`
- Candidate count and deduplicated count
- Selected `SelectedEvidence[]` items with `provenance_hash`
- `ClaimEvidenceBinding[]` mapping synthesized text to canonical evidence items.

Replay checks compare the `provenance_hash` and `claim_hash` to prove historical reproduction without silent drift.
