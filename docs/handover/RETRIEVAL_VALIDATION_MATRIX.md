# Retrieval Validation Matrix

## Executed tests

| Surface | Reproducible command / evidence | Result |
|---|---|---|
| Baseline, before remediation | `python -m pytest -q backend/tests/test_sanskrit_decoder.py backend/tests/test_phase2_sanskrit_decoder_knowledge_graph.py backend/tests/test_knowledge_convergence.py backend/tests/test_retriever_quality.py backend/tests/test_kosha_evidence_selection.py backend/tests/test_semantic_authority_governance.py tests/test_curriculum_truth_validation.py` | **139 passed** in 146.74s. |
| Focused post-remediation suite | `python -m pytest -q -p no:cacheprovider --basetemp="$env:TEMP\ug-ho-02-pytest" backend/tests/test_sanskrit_decoder.py backend/tests/test_sanskrit_schema_immutability.py backend/tests/test_phase2_sanskrit_decoder_knowledge_graph.py backend/tests/test_knowledge_convergence.py backend/tests/test_knowledge_enrichment_convergence.py backend/tests/test_phase2_knowledge_convergence_trust_validation.py backend/tests/test_retriever_quality.py backend/tests/test_kosha_evidence_selection.py backend/tests/test_kosha_answer_synthesis.py backend/tests/test_semantic_authority_governance.py backend/tests/test_rag_health.py tests/test_curriculum_truth_validation.py tests/test_masterdb_retrieval_filters.py` | **232 passed, 1 skipped** in 203.92s. The skipped case is the expected no-committed-index RAG health guard. Use a fresh temporary directory for `--basetemp`; cache writes are disabled. |
| Sanskrit registry mutation regression | `backend/tests/test_sanskrit_schema_immutability.py` | Passed in the post-remediation suite. The caller-owned input list cannot mutate a registered concept; dictionary export remains a list. |
| MasterDB filter regressions | `tests/test_masterdb_retrieval_filters.py` | Passed in the post-remediation suite. Grade/medium/subject mismatches return no candidates; a matching filter still retrieves the record. |
| Partial claim-provenance regression | `backend/tests/test_knowledge_convergence.py::test_unmatched_answer_claim_is_not_bound_to_unrelated_evidence` | **3 passed** in the focused check, together with the no-evidence and canonical-binding tests. Unmatched text is now `UNVERIFIED_FALLBACK`, with zero confidence and no canonical object. |
| Authority registry path regressions | `backend/tests/test_phase2_knowledge_convergence_trust_validation.py::test_faiss_authority_map_rebuild_path_points_to_existing_builder` and `test_rebuildable_authority_sources_have_existing_paths` | Passed in the post-remediation suite; all rebuildable entries resolve to existing files/directories. |

## Data and runtime probes

| Probe | Result | Interpretation |
|---|---|---|
| `validate_masterdb` on `masterdb/balbharti/canonical_dataset.json` | 42 records; 0 valid; no duplicate IDs; all 42 missing `source_lineage.source_reference`; `canonical_authority_granted` is false. | A known provenance blocker remains. No references or signatures were manufactured. |
| `build_coverage_report` on the same records | 4 of 160 expected grade/subject/medium cells, **2.5%**; grades 1-3, English/Mathematics/Science, Marathi Medium only. | Dataset coverage is far narrower than the declared 10-grade, 8-subject, 2-medium matrix. |
| `get_rag_health()` read-only probe in the current checkout | `healthy`; 75 documents, 160 chunks, 384 dimensions, `source_manifest_current=true`. | This is a local generated index, not an artifact in the uploaded ZIP. Do not use it to certify archive portability or a deployed service. |
| `backend/tests/test_rag_health.py` | Skipped by its own guard because no FAISS index is committed. | Expected for an archive that contains no portable generated index. |
| External Vijay/BHIV integration | Not run. | No external credentials, deployment endpoints, or participation from Vijay were available in this task. Local `TestClient` success is not live integration evidence. |

## Final focused command

Run from the repository root in PowerShell, replacing the `--basetemp` value with a new, empty temporary directory:

```powershell
python -m pytest -q -p no:cacheprovider --basetemp="$env:TEMP\ug-ho-02-pytest" `
  backend/tests/test_sanskrit_decoder.py `
  backend/tests/test_sanskrit_schema_immutability.py `
  backend/tests/test_phase2_sanskrit_decoder_knowledge_graph.py `
  backend/tests/test_knowledge_convergence.py `
  backend/tests/test_knowledge_enrichment_convergence.py `
  backend/tests/test_phase2_knowledge_convergence_trust_validation.py `
  backend/tests/test_retriever_quality.py `
  backend/tests/test_kosha_evidence_selection.py `
  backend/tests/test_kosha_answer_synthesis.py `
  backend/tests/test_semantic_authority_governance.py `
  backend/tests/test_rag_health.py `
  tests/test_curriculum_truth_validation.py `
  tests/test_masterdb_retrieval_filters.py
```

These are focused architecture/regression tests, not the entire repository test suite. Results were obtained against the checked-out branch, whose differences from the uploaded archive are documented in the baseline. The index builder itself was not executed because it writes the active RAG pointer and requires the embedding dependencies.

---

## UG-HO-02 Continuation — Archive Parity Validation

**Updated:** 2026-11-03 (continuation pass)

| Probe | Result | Interpretation |
|---|---|---|
| `bhiv-uniguru-main/backend/retrieval/retriever.py` vs checkout | Archive has 6-stage cascade including `_try_balbharati`, `_try_sanskrit_decoder`, reranker, and `utils/rag_logger`. Checkout has 4-stage cascade without those. | Checkout is missing the Balbharati hybrid retriever and Sanskrit decoder dispatch. These are not in the UG-HO-02 fixes; they are pre-existing archive capabilities. |
| `bhiv-uniguru-main/backend/retrieval/balbharati/` | 8 files present in archive; absent from checkout. | Entire Balbharati PDF/BM25 retrieval subsystem is archive-only. |
| `bhiv-uniguru-main/uniguru_sanskrit_decoder/` | 7 files present in archive; absent from checkout. | Root-level Sanskrit decoder package is archive-only. |
| `contracts/schemas.py` | Absent from both checkout and archive. | TANTRA schema compliance requirement is unmet in both sources. |
| `masterdb/balbharti/canonical_dataset.json` in archive | Same 42 records, same missing `source_reference`. | Provenance blocker is identical in both sources. |
| FAISS active-pointer protection | `--output-root` flag does not protect `active_index.json`; `RAG_ROOT` is hardcoded. | Safe build requires monkeypatching `RAG_ROOT`. Procedure documented; not executed. |
| Archive `docs/handover/` | Absent from archive. | All 10 handover documents are checkout-only. |
