# Known Knowledge and Retrieval Gaps

This list separates confirmed data/code gaps from work that needs source-owner decisions. Existing data was not deleted or rewritten to make the audit appear green.

## Confirmed blockers

### 1. MasterDB provenance gate fails on every canonical row

`masterdb/balbharti/canonical_dataset.json` contains 42 records. Each has publisher, ISBN, edition, page, source hash, and other lineage metadata, but all lack `source_lineage.source_reference`. `masterdb/masterdb_validation.py::validate_masterdb` marks all 42 invalid for `missing_source_reference` and sets `canonical_authority_granted` to false. `canonical_dataset_manifest.json` separately says `ALL_VERIFIED`. This status contradiction must be resolved from authoritative source material; do not synthesize URL or citation values or recompute signatures without evidence.

### 2. Declared curriculum coverage is not present

The coverage validator expects 10 grades x 8 subjects x 2 mediums (160 cells). The dataset supplies 4 cells (2.5%): grades 1-3, English/Mathematics/Science, Marathi Medium only. Grades 4-10, five subjects, and English Medium are absent. Catalog metadata or sample/experimental files should not be counted as canonical answer content.

### 3. Archive and checkout are different source revisions

The ZIP contains 4,890 outer-tree files. The existing checkout has substantial same-path byte differences and archive-only paths. Examples that affect behavior: archive-only `backend/retrieval/unified_rag_engine.py` and its dispatch; changed scoring/threshold behavior in `retrieval/retrieval_engine.py`; differing ontology seed data and tests. The worktree was isolated on `ug-ho-02-knowledge-retrieval`, but that branch started from the existing checkout, not a reconstructed ZIP tree. The focused tests therefore validate the checkout revision, not every ZIP-only file.

### 4. Dense index does not establish canonical-object provenance

`backend/scripts/build_rag_index.py` reads Markdown under `backend/knowledge/` and writes file/chunk metadata. It does not read MasterDB/Kosha or store `canonical_object_id` in its SQLite chunk schema. The former policy document described a canonical-object mapping that this builder does not provide. The documentation and authority-map rebuild path are corrected; the storage contract itself was not changed.

### 5. Duplicate authority labels need source-owner confirmation

`AKASHIC` and `KOSHA_JSON` are listed as distinct canonical source keys but resolve to the same Kosha data family in this repository. They may be semantic labels for distinct lineages, but the archive does not establish that distinction. Do not copy records or merge the policy keys until Vijay/MDU confirms the intended source identity and provenance rules.

## Remaining provenance risk

The active `backend/convergence/convergence_runtime.py` now marks a sentence with no token overlap to selected evidence as `UNVERIFIED_FALLBACK`. The separate `retrieval/knowledge_convergence.py::bind_answer_claims` helper still returns the entire answer as one `answer_summary` bound only to the first selected evidence. No production call site was found for this helper in the searched Python paths; do not treat it as sentence-level evidence validation.

## Integration and release limits

- No live Vijay/BHIV service was called. External endpoint availability, credentials, replay behavior, data sync, and deployment status remain unverified and may require Vijay's access.
- The archive contains no portable versioned FAISS/SQLite index. The checked-out environment has a local generated index that reported healthy, but that is not evidence the uploaded archive can run dense retrieval as-is.
- The index builder changes the active pointer and requires embeddings. It was not invoked. Any next build should redirect/patch all output roots in a disposable test fixture before generating an index.
- The embedded 1,929-file `bhiv-uniguru-main/` subtree was not deleted or treated as a second runtime source.

## Next-build tasks

Three bounded follow-up tasks with objectives, acceptance criteria, dependencies, and reproducible test commands are recorded in `review_packets/REVIEW_PACKET.md`.

---

## UG-HO-02 Continuation — Updated Gap Status

**Updated:** 2026-11-03 (continuation pass)

### Gap 1: MasterDB provenance — root cause confirmed

The `source_reference` field was never populated by the ingestion script. All 42 records have `publisher`, `isbn`, `edition`, `page`, and `source_hash` but no `source_reference` key. The validator hard-fails on this missing key. The manifest was written by a separate script that did not invoke the validator, creating the `ALL_VERIFIED` / `0 valid` contradiction.

**Authoritative source required from Vijay/MDU:**
- Approved citation format for `source_reference`.
- Confirmation that ISBNs `978-81-7657-001-2` through `978-81-7657-004-3` resolve to licensed, ingestible Balbharti artifacts.
- Approval of the migration script before any data is written.

### Gap 2: Curriculum coverage — missing cells documented

Present: 4 cells (Grade 1 Math MM, Grade 2 Math MM, Grade 1 English MM, Grade 3 Science MM). Missing: all English Medium cells (160 − 4 = 156 cells absent), grades 4–10 entirely, subjects EVS/History/Geography/Marathi/Civics entirely. Official catalog metadata in `masterdb/balbharti/official_catalog/` is not answer content and must not be counted.

### Gap 3: Archive-only capabilities not in checkout

The ZIP contains `backend/retrieval/balbharati/` (8 files), `uniguru_sanskrit_decoder/` (7 files), `backend/retrieval/reranker.py`, `backend/utils/rag_logger.py`, and a 6-stage retrieval cascade. None of these are in the checkout branch. Vijay must confirm the intended merge base.

### Gap 4: `contracts/schemas.py` absent from both sources

Neither the checkout nor the archive contains `contracts/schemas.py`. This is a TANTRA schema compliance requirement. The schema specification must be provided by Vijay/TANTRA before implementation.

### Gap 5: FAISS active-pointer protection

The builder's `--output-root` flag does not protect `backend/RAG/active_index.json` because the pointer write is hardcoded to `RAG_ROOT`. The safe build procedure requires monkeypatching `RAG_ROOT` before import. This procedure is documented in `KNOWLEDGE_AND_RETRIEVAL_BASELINE.md` Section 6 and has not been executed.
