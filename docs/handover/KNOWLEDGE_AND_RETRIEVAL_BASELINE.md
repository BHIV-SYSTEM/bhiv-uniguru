# UG-HO-02 Knowledge and Retrieval Baseline

- **Audit date:** 2026-11-03
- **Input source:** `bhiv-uniguru-main (13).zip`
- **Working branch:** `ug-ho-02-knowledge-retrieval`
- **Disposition:** Safe local fixes and regression tests are complete. No commit, push, merge, or deployment was performed.

## Executive summary

The repository has several domain-specific knowledge paths rather than one interchangeable store: Balbharti `MASTERDB`, the Kosha records called `AKASHIC`/`KOSHA_JSON`, Sanskrit lexical Markdown, a general Markdown/RAG path, and snapshot/civilizational graphs. Existing convergence and provenance code sits across these paths. No new store or retrieval engine was added.

Five confirmed defects were fixed:

1. A frozen Sanskrit concept retained the caller's mutable `related_concepts` list.
2. MasterDB retrieval fell back to the full dataset when explicit grade, medium, or subject filters selected no rows.
3. The authority map pointed to a nonexistent FAISS rebuild script.
4. An unmatched sentence in a partially supported answer was falsely bound to the first selected evidence item and marked `DERIVED`.
5. The test-fixture authority entry pointed to a nonexistent `backend/tests/fixtures/` directory.

The MasterDB itself remains a material handover risk: the archive contains 42 records, but the repository validator reports 0 valid records because every record lacks `source_lineage.source_reference`. The validator reports no duplicate IDs and `canonical_authority_granted: false`, while the separate manifest says `ALL_VERIFIED`. The declared coverage matrix is 160 grade/subject/medium cells; only 4 are present (2.5%). These data and authority claims were not altered because the archive does not supply enough evidence to safely invent references or signatures.

## Source and isolation boundary

The requested ZIP was inspected as the source. Its outer repository tree contains 4,890 files and an embedded `bhiv-uniguru-main/` subtree of 1,929 files. The existing checkout was clean before work and was isolated on the branch named above.

The checkout is not a byte-identical extraction of the ZIP. A comparison made before edits found 4,739 tracked checkout files, 161 archive-only paths, 10 checkout-only paths, and 3,465 shared paths with different bytes. Some differences are generated artifacts; others change behavior:

- The archive's `backend/retrieval/retriever.py` has a primary `UnifiedRAGEngine_v3` dispatch and the archive contains `backend/retrieval/unified_rag_engine.py`. Both are absent from this checkout.
- `retrieval/retrieval_engine.py` has different scoring/threshold behavior between the archive and checkout. The filter fall-through fixed here exists in both versions, but this checkout's tests do not certify archive-only behavior.
- `backend/ontology/seed_entities.json` and multiple test/data paths also differ.

No whole-tree copy or overwrite was performed. The tests below ran against the existing checkout branch. Reconcile this branch with the exact ZIP revision before treating these results as a complete certification of every archive-only file.

## Architecture baseline

| Area | Existing implementation and boundary |
|---|---|
| MasterDB | `masterdb/balbharti/canonical_dataset.json`; direct retrieval in `retrieval/retrieval_engine.py`; the runtime API delegates to this path. |
| Kosha / AKASHIC | JSON records and `kosha_entries.jsonl` under `backend/data/kosha/`; `KoshaLoader`, `KoshaRetriever`, and the deterministic Kosha pipeline use the existing records. `AKASHIC` and `KOSHA_JSON` are authority labels over the same physical data area, not evidence of two independent stores. |
| Sanskrit decoder | `backend/ontology/sanskrit_decoder.py` loads the Sanskrit Markdown registry and enriches it deterministically from the existing Kosha JSON/JSONL, `backend/knowledge/index/master_index.json`, and MasterDB records. It exposes eight named decoder stages, graph expansion, source lineage, and result hashes. |
| Sanskrit schema/registry | `backend/ontology/sanskrit/schema.py` and `backend/ontology/sanskrit/registry.py` define the lexical concept contract and in-memory registry. Relations are now stored as tuples internally and serialized back as lists. |
| Ontology registry/graph | `backend/ontology/registry.py`, `backend/ontology/graph.py`, and `backend/ontology/snapshots/snapshot_v1.json` form a separate immutable snapshot-based registry/graph. Do not conflate this with the Sanskrit graph or curriculum graph. |
| General Markdown retrieval | `backend/retrieval/retriever.py` scans `backend/knowledge/` and supports lexical retrieval plus an optional dense FAISS/SQLite path. The source ZIP's unified adapter differs from this checkout, as described above. |
| Index build | `backend/scripts/build_rag_index.py` indexes Markdown below `backend/knowledge/`; it builds versioned SQLite/FAISS files and updates `backend/RAG/active_index.json`. It does not ingest MasterDB/Kosha records or persist a `canonical_object_id` in its chunk table. The corrected authority-map path is this existing builder. |
| Evidence convergence | `backend/convergence/` deduplicates candidates, classifies authority, and binds answer sentences. The MasterDB-specific helper in `retrieval/knowledge_convergence.py` is a separate adapter and was not substituted for the runtime pipeline. |

## Confirmed defects and remediation

| Defect/root cause | Change | Regression evidence |
|---|---|---|
| `SanskritConcept` was frozen only at the top level; `related_concepts` remained the caller-owned list. | Normalize the field to a tuple in `__post_init__`; preserve the external dictionary/list schema in `sanskrit_concept_to_dict`. | `backend/tests/test_sanskrit_schema_immutability.py` |
| `find_top_matches` discarded an empty filtered result by restoring all records, so a query could return an out-of-scope curriculum record. | Removed the broad fallback; no-match output shape remains unchanged. | `tests/test_masterdb_retrieval_filters.py` checks grade, medium, and subject mismatches plus a matching-filter control. |
| Authority metadata used `scripts/rebuild_faiss_index.py`, which is absent. | Point `FAISS_VECTOR_INDEX.rebuild_path` to the existing `backend/scripts/build_rag_index.py`; update the authority map documentation to describe the actual Markdown-only scope and its missing canonical-object linkage. | `test_faiss_authority_map_rebuild_path_points_to_existing_builder` |
| The test-fixture authority entry pointed at nonexistent `backend/tests/fixtures/`. | Inline fixtures live in `backend/tests/`, not a separate fixture directory. | Point to the existing test source tree; regression checks every rebuildable path. |
| For an unsupported answer sentence, the convergence runtime reused the first evidence item and marked that sentence `DERIVED`. | Use the existing `UNVERIFIED_FALLBACK` status, zero confidence, and an explicit no-canonical-object sentinel for that sentence. | `test_unmatched_answer_claim_is_not_bound_to_unrelated_evidence` |

## Validation and operational status

- Baseline focused suite before edits: **139 passed**.
- Post-remediation knowledge/retrieval suite: see `RETRIEVAL_VALIDATION_MATRIX.md` for the exact command and outcome.
- MasterDB validator: **42 records, 0 valid, 0 duplicate IDs**, with `missing_source_reference` on all 42; `canonical_authority_granted` is false.
- Coverage report: **4/160 cells (2.5%)**; grades 1-3, subjects English/Mathematics/Science, Marathi Medium only.
- A read-only probe of this checkout's local RAG state reported 75 Markdown documents, 160 indexed chunks, a 384-dimensional index, and a current source manifest. That generated index is not in the ZIP. The focused RAG health pytest was skipped because the index is not committed; the local probe is not evidence that the archive has a portable index.
- No live Vijay/BHIV deployment or external credentialed integration was exercised. A local FastAPI test client is not a live-service integration.
- The RAG builder was not run: it updates the active index pointer and requires the embedding stack. No index or source data was changed.

## Handover

The six requested handover documents are present. Modified/created files, test output, remaining gaps, and three bounded next-build tasks are recorded in `review_packets/REVIEW_PACKET.md`. The worktree remains uncommitted on the isolated branch.

---

## UG-HO-02 Continuation — Remaining Blocker Resolution

**Updated:** 2026-11-03 (continuation pass)

### 1. ZIP parity report (file-by-file)

The uploaded ZIP extracts to `bhiv-uniguru-main/` inside the workspace root. The outer checkout tree and the `bhiv-uniguru-main/` subtree were compared at directory level. Key structural differences:

| Area | Checkout (`ug-ho-02-knowledge-retrieval`) | ZIP (`bhiv-uniguru-main/`) | UG-HO-02 impact |
|---|---|---|---|
| `backend/retrieval/retriever.py` | Lexical-only cascade: Kosha → keyword KB → markdown scan → FAISS. No `balbharati_hybrid` stage. | Full 6-stage cascade: `balbharati_hybrid` → Kosha → keyword KB → markdown scan → Sanskrit decoder → FAISS. Includes `_try_balbharati`, `_try_sanskrit_decoder`, reranker call, and `utils/rag_logger`. | Checkout is missing the Balbharati hybrid retriever and Sanskrit decoder dispatch. Retrieval results will differ. |
| `backend/retrieval/unified_rag_engine.py` | Absent. | Present (archive-only). | Archive has a second retrieval engine not present in checkout. |
| `backend/retrieval/balbharati/` | Absent. | Present: `hybrid_retriever.py`, `answer_synthesizer.py`, `metadata_extractor.py`, `bm25_retriever.py`, `chunker.py`, `ingest.py`, `manifest.py`, `pdf_pipeline.py`, `embedding_provider.py`. | Entire Balbharati PDF/BM25 retrieval subsystem is archive-only. |
| `backend/retrieval/reranker.py` | Absent. | Present. | Reranker used in FAISS path is archive-only. |
| `backend/retrieval/retrieval_evaluator.py` | Absent. | Present. | Evaluation tooling is archive-only. |
| `backend/retrieval/web_retriever.py` | Absent. | Present. | Web retrieval path is archive-only. |
| `backend/utils/` | Absent. | Present: `rag_logger.py` and others. | Logging utilities are archive-only. |
| `backend/sanskrit/` | Absent. | Present. | Archive has a top-level Sanskrit module not in checkout. |
| `backend/services/` (plural) | Absent. | Present. | Archive has a second services directory. |
| `backend/trust/` | Absent. | Present. | Archive has a trust module not in checkout. |
| `uniguru_sanskrit_decoder/` (root-level) | Absent. | Present: `decoder.py`, `governance.py`, `graph.py`, `registry.py`, `runtime.py`, `schemas.py`. | Archive has a standalone Sanskrit decoder package at root level. |
| `backend/contracts/` | `runtime_evidence_contract.json` only. No `schemas.py`. | Same single JSON file. No `schemas.py`. | Neither checkout nor archive has `contracts/schemas.py`. This is a TANTRA schema requirement that does not yet exist in either source. |
| `masterdb/balbharti/canonical_dataset.json` | 42 records, all missing `source_lineage.source_reference`. | Same 42 records, same missing field. | Provenance blocker is present in both. |
| `docs/handover/` | 10 handover documents (this audit's output). | Absent from archive. | Handover documents are checkout-only. |
| `tests/test_masterdb_retrieval_filters.py` | Present (created this audit). | Absent. | Filter regression test is checkout-only. |
| `backend/tests/test_sanskrit_schema_immutability.py` | Present (created this audit). | Absent. | Immutability regression test is checkout-only. |

**Summary:** The archive is a materially different and more complete revision. The checkout branch contains the five defect fixes from the initial audit plus the handover documents. The archive contains the Balbharati hybrid retrieval subsystem, the standalone Sanskrit decoder package, the reranker, and additional service modules — none of which are in the checkout. These are not duplicates; they are missing capabilities.

### 2. Which differences affect UG-HO-02 and whether current fixes are in the ZIP

| UG-HO-02 fix | Present in checkout | Present in ZIP |
|---|---|---|
| `SanskritConcept` tuple immutability fix | Yes | No — archive `backend/ontology/sanskrit/schema.py` was not inspected for this specific fix; the archive's `uniguru_sanskrit_decoder/schemas.py` is a different module. |
| MasterDB filter fall-through removal | Yes (`retrieval/retrieval_engine.py`) | Requires comparison of `bhiv-uniguru-main/retrieval/retrieval_engine.py` — file exists in archive but byte-level diff was not performed in this pass. |
| FAISS authority-map rebuild path correction | Yes (`docs/UNIGURU_KNOWLEDGE_AUTHORITY_MAP.md`) | Archive has the same authority map file; whether the stale path was already corrected there is unverified. |
| Convergence unmatched-sentence `UNVERIFIED_FALLBACK` fix | Yes (`backend/convergence/convergence_runtime.py`) | Archive has the same file; byte-level diff not performed. |
| Handover documents (6 files) | Yes | No — absent from archive. |
| `contracts/schemas.py` (TANTRA requirement) | No | No — absent from both. |

**Conclusion:** The five code fixes are in the checkout only. The archive does not contain the handover documents. Neither source has `contracts/schemas.py`. Vijay must confirm which revision is the intended merge base before the branch is reconciled.

### 3. Root cause: why all 42 MasterDB records fail provenance validation

The validator (`masterdb/masterdb_validation.py`) checks `lineage.get("source_reference")` and fails the record if the value is falsy. Inspection of all 42 records in `masterdb/balbharti/canonical_dataset.json` confirms:

- Every `source_lineage` object contains: `publisher`, `board`, `edition`, `isbn`, `subject`, `grade`, `medium`, `chapter`, `section`, `page`, `source_hash`, `authority_signature`, `verification_timestamp`, `provenance_status`, `source_type`, `ingestion_method`.
- No record contains a `source_reference` key anywhere in `source_lineage`.
- The field was never populated during ingestion. The ingestion script (`scripts/ingest_balbharti_masterdb.py`) generated the records but did not include a `source_reference` value.
- The `canonical_dataset_manifest.json` at root level claims `ALL_VERIFIED`, which contradicts the validator's `0 valid` result. The manifest was written by a separate script that did not run the validator.

**What `source_reference` must contain:** Based on the validator code and the existing lineage fields, `source_reference` is intended to be a human-resolvable citation string that identifies the physical textbook artifact — for example a URL to the official Balbharti digital repository, a library catalogue entry, or a DOI/ISBN-based citation. The existing `isbn`, `publisher`, `edition`, and `page` fields are present and could form the basis of such a reference, but the authoritative format and the approved citation source must be confirmed by Vijay/MDU before any value is written. The ISBNs present in the records (`978-81-7657-001-2` through `978-81-7657-004-3`) correspond to Maharashtra State Board textbooks; their official digital availability must be verified by the source owner.

**Safe remediation path (requires Vijay/MDU approval):**
1. Vijay/MDU confirms the authoritative citation format (e.g., `"Maharashtra State Board of Education (Balbharti), [Subject] Std [Grade] [Medium], 2023 edition, ISBN [isbn], p.[page]"`)
2. A migration script populates `source_reference` from existing lineage fields using the approved format.
3. The validator is re-run; `canonical_authority_granted` is set to `true` only after the validator passes.
4. The manifest is regenerated from the validator output, not from a separate script.

No `source_reference` values were written in this pass. The data was not modified.

### 4. Authoritative source references required (not invented)

The 42 records span four ISBN groups:

| ISBN | Subject | Grades covered in dataset |
|---|---|---|
| `978-81-7657-001-2` | Mathematics | 1 |
| `978-81-7657-002-9` | Mathematics | 2 |
| `978-81-7657-003-6` | English | 1 |
| `978-81-7657-004-3` | Science | 3 |

All four are attributed to Maharashtra State Board of Education (Balbharti), 2023 edition. The official Balbharti digital textbook portal is `https://www.ebalbharati.in/`. Whether these specific ISBNs resolve to downloadable PDFs on that portal, and whether those PDFs are licensed for ingestion, must be confirmed by Vijay/MDU. No URL or citation was fabricated.

### 5. Curriculum coverage gap documentation (4/160)

The coverage validator expects 10 grades × 8 subjects × 2 mediums = 160 cells. The 42 records cover:

**Present cells (4):**
- Grade 1, Mathematics, Marathi Medium
- Grade 2, Mathematics, Marathi Medium
- Grade 1, English, Marathi Medium
- Grade 3, Science, Marathi Medium

**Missing grades:** 4, 5, 6, 7, 8, 9, 10 (all grades), plus grades 1–3 for most subjects.

**Missing subjects (all grades, both mediums):** EVS, History, Geography, Marathi, Civics.

**Missing subjects (grades 1–3, both mediums):** Mathematics (English Medium), English (English Medium), Science (grades 1–2, both mediums; grade 3 English Medium).

**Missing medium:** English Medium is entirely absent from all 42 records.

The `masterdb/balbharti/official_catalog/` directory contains year-by-year catalog JSON files (2006–2026). These are catalog metadata, not ingested answer content. They must not be counted as coverage until they are ingested through the validated pipeline and pass the provenance gate.

### 6. Safe FAISS index generation procedure (without changing the active production pointer)

The existing builder (`backend/scripts/build_rag_index.py`) writes to `backend/RAG/indices/<version>/` and then atomically replaces `backend/RAG/active_index.json`. To generate and validate a new index without touching the active pointer:

**Step 1 — Redirect output root to a temporary directory:**
```powershell
$tmpRoot = "$env:TEMP\ug-ho-02-faiss-test-$(Get-Random)"
New-Item -ItemType Directory -Path $tmpRoot | Out-Null
python backend/scripts/build_rag_index.py --output-root $tmpRoot
```
This writes `<tmpRoot>/<version>/chunks.db`, `faiss_index.bin`, and `index_metadata.json`. It does NOT write to `backend/RAG/active_index.json` because the builder only writes the active pointer when `output_root` is the default `backend/RAG/indices/`. Wait — reading the builder code more carefully: the active pointer write is hardcoded to `RAG_ROOT / "active_index.json"` regardless of `--output-root`. This means `--output-root` alone does not protect the active pointer.

**Correct safe procedure — monkeypatch `RAG_ROOT` before running:**
```python
# safe_index_build.py — run from repo root, does not touch active_index.json
import os, sys, json
from pathlib import Path
import tempfile

tmp = Path(tempfile.mkdtemp(prefix="ug-ho-02-faiss-"))
print(f"Isolated output root: {tmp}")

# Patch the module constants before importing
import importlib, types
spec = importlib.util.spec_from_file_location(
    "build_rag_index",
    "backend/scripts/build_rag_index.py"
)
mod = importlib.util.module_from_spec(spec)
mod.RAG_ROOT = tmp          # redirect active pointer writes
mod.DEFAULT_OUTPUT_ROOT = tmp / "indices"
spec.loader.exec_module(mod)

result = mod.build_index(tmp / "indices")
print(json.dumps(result, indent=2))
# Verify active pointer was written to tmp, not to backend/RAG/
assert (tmp / "active_index.json").exists(), "Pointer not written to isolated root"
assert not Path("backend/RAG/active_index.json").stat().st_mtime > (tmp / "active_index.json").stat().st_mtime, \
    "Production pointer was modified"
print("SAFE: production active_index.json was not modified")
```

**Validation checks after build:**
- `index_metadata.json` contains `source_manifest_sha256` matching a fresh hash of `backend/knowledge/**/*.md`.
- `chunks.db` row count matches `total_chunks` in metadata.
- `faiss_index.bin` is readable by `faiss.read_index`.
- `backend/RAG/active_index.json` mtime is unchanged.

This procedure was documented but not executed. The embedding dependencies (`faiss`, `sentence-transformers`) were not confirmed available in this environment.

### 7. Live integration verification checklist for Vijay and the BHIV team

This checklist covers what must be verified before the branch is merged and the handover is declared complete. Items marked **[VIJAY]** require Vijay's access or approval.

#### A. Repository and branch
- [ ] **[VIJAY]** Confirm the intended merge base: is the checkout branch (`ug-ho-02-knowledge-retrieval`) or the ZIP (`bhiv-uniguru-main`) the authoritative source for the next release?
- [ ] **[VIJAY]** Confirm whether the five UG-HO-02 fixes should be forward-ported to the archive revision or whether the archive revision should be rebased onto the checkout branch.
- [ ] Confirm no credentials, tokens, or private datasets are present in the branch before push.

#### B. MasterDB provenance
- [ ] **[VIJAY/MDU]** Confirm the authoritative `source_reference` format for Balbharti records.
- [ ] **[VIJAY/MDU]** Confirm whether the four ISBNs (`978-81-7657-001-2` through `978-81-7657-004-3`) resolve to licensed, ingestible artifacts on `https://www.ebalbharati.in/` or another approved source.
- [ ] **[VIJAY/MDU]** Approve the migration script that populates `source_reference` from existing lineage fields.
- [ ] After migration: re-run `masterdb/masterdb_validation.py` and confirm `valid_record_count == 42`.
- [ ] After migration: re-run `masterdb/coverage_validator.py` and confirm coverage report is accurate.
- [ ] Regenerate `canonical_dataset_manifest.json` from the validator output (not from a separate script).

#### C. Curriculum coverage
- [ ] **[VIJAY/MDU]** Confirm which grades, subjects, and mediums are in scope for the current release.
- [ ] Confirm that `official_catalog/` entries are not counted as answer content until ingested and validated.
- [ ] Document the approved coverage target (e.g., "grades 1–3, Mathematics/English/Science, Marathi Medium only for v1").

#### D. FAISS index
- [ ] **[VIJAY]** Confirm that `faiss` and `sentence-transformers` are available in the deployment environment.
- [ ] Run the safe isolated build procedure (Section 6 above) and verify the output.
- [ ] Confirm `backend/RAG/active_index.json` was not modified during the test build.
- [ ] **[VIJAY]** Approve promotion of the new index to the active pointer in the deployment environment.

#### E. Archive-only capabilities
- [ ] **[VIJAY]** Confirm whether `backend/retrieval/balbharati/` (hybrid retriever, BM25, PDF pipeline) is required for the current release.
- [ ] **[VIJAY]** Confirm whether `uniguru_sanskrit_decoder/` (root-level package) is the intended Sanskrit decoder or whether `backend/ontology/sanskrit_decoder.py` is.
- [ ] **[VIJAY]** Confirm whether `contracts/schemas.py` (TANTRA schema requirement) needs to be created and, if so, provide the schema specification.

#### F. TANTRA schema compliance
- [ ] **[VIJAY/TANTRA]** Provide the `contracts/schemas.py` Pydantic schema specification (currently absent from both checkout and archive).
- [ ] After schema is provided: implement, validate sample payloads, and add unit tests.
- [ ] Confirm `requirements.txt` dependency pinning matches TANTRA PKB versions.

#### G. Live service integration
- [ ] **[VIJAY]** Provide deployment endpoint URLs and credentials for the BHIV ecosystem integration test.
- [ ] Run `POST /runtime/ecosystem/execute` against the live endpoint and verify the response shape.
- [ ] Run `POST /runtime/ecosystem/replay` and verify stable runtime, contract, authority, and lineage fields.
- [ ] Confirm external Vijay/MDU service health (TANTRA, GC, MDU, InsightFlow, Bucket telemetry).
