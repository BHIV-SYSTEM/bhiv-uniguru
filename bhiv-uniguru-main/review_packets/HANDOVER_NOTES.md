# Handover Notes

## Balbharti Curriculum Sprint Handover

- MASTERDB now contains 2,560 Balbharti synthetic seed records across grades 1-10, English Medium, Marathi Medium, and eight subjects.
- Retrieval is integrated through the canonical runtime path: `backend/service/uniguru_runtime_api.py -> retrieval/retrieval_engine.py -> learning_runtime/learning_intelligence.py -> backend/governance/constitutional_runtime.py`.
- Validation artifacts are regenerated:
  - `curriculum/coverage_report.json`
  - `masterdb/balbharti/ingestion_manifest.json`
  - `review_packets/proof_logs/balbharti_masterdb_ingestion_proof.json`
  - `review_packets/proof_logs/curriculum_integrity_report.json`
  - `review_packets/proof_logs/retrieval_quality_report.json`
  - `review_packets/proof_logs/learning_intelligence_demo.json`
- The latest runtime proof is `review_packets/proof_logs/uniguru_runtime_execution_latest.json` for Grade 10 Science / Force and Motion.
- Important caveat: this is a synthetic expansion seed with `provenance_status: sample_seed`; canonical authority remains false until verified textbook page-level ingestion is completed.

## Current Limitations

- Kosha source entries still contain OCR artifacts and thin fragments; the validator now rejects weak entries instead of stretching them into answers.
- Epistemic confidence intentionally caps OCR derivative sources; a strong retrieval match can still produce moderate confidence.
- Legacy FAISS/LLM helper code remains below the early deterministic return in `backend/service/api.py`; endpoint execution no longer reaches it, but cleanup is recommended.
- Stored Kosha domain labels are inconsistent; runtime ontology normalization compensates.
- `bucket_proof` is emitted in every deterministic payload and is ready for external Bucket transport, but this pass writes file-backed proof logs only.

## Next Risks

- New ingestion flows must tag entries with canonical entities before activation.
- The ontology seed needs Vijay/Soham review before it becomes a formal TANTRA contract.
- Proof execution should be pinned in CI by Alay for environment-stable validation.
- Source hierarchy rules in `backend/governance/source_governance.py` should be reviewed when new canonical corpora are added.

## Integration Dependencies

- Vijay: trace contract confirmation for TANTRA execution chain.
- Soham: canonical entity taxonomy and semantic mapping review.
- Alay: CI wiring for `python backend/run_proof_log.py` and `python backend/run_retrieval_benchmark.py`.
- Vinayak: deterministic verification of trace continuity across `trace_id`, `output_contract`, `downstream_execution`, and `bucket_proof`.
# 2026-07-03 BHIV Ecosystem Handover

UniGuru now has a BHIV ecosystem acceptance path with a governed Mitra-facing interface.

## Central Depository Submission

- Primary packet: `review_packets/REVIEW_PACKET.md`
- Execution summary: `review_packets/execution_summary.md`
- Acceptance report: `review_packets/validation_reports/ecosystem_acceptance_report.json`
- API response log: `review_packets/logs/ecosystem_acceptance_api_responses.json`
- Deployment validation: `review_packets/deployment_proof/ecosystem_deployment_validation.json`
- Runtime proof: `review_packets/integration_proof/ecosystem_execution_latest.json`
- Replay proof: `review_packets/integration_proof/replay_verification_latest.json`

## Operational Commands

```powershell
.venv\Scripts\python.exe -m pytest backend/tests/test_constitutional_runtime.py backend/tests/test_ecosystem_integration.py -q
.venv\Scripts\python.exe scripts\run_ecosystem_acceptance.py
```

## Production Notes

- Internal BHIV execution uses `POST /runtime/ecosystem/execute`.
- Vijay replay acceptance uses `POST /runtime/ecosystem/replay`.
- Mitra uses `POST /mitra/ecosystem/ask`, which redacts internal governance details.
- Remote Bucket emission requires deployment environment variables for the Bucket endpoint and token.
