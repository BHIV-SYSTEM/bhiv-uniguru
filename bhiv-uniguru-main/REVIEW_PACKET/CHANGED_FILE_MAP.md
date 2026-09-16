# Changed File Map — Knowledge Convergence & Trust Validation Sprint

## New Files Created

| File Path | Purpose |
|---|---|
| `backend/convergence/__init__.py` | Package exports for convergence module |
| `backend/convergence/authority_contract.py` | AuthorityTier enum & KnowledgeAuthorityMap registry |
| `backend/convergence/canonical_object.py` | CanonicalKnowledgeObject schema conforming to MDU requirements |
| `backend/convergence/retrieval_evidence_contract.py` | RetrievalRunRecord, RetrievedEvidenceItem, ClaimEvidenceBinding |
| `backend/convergence/convergence_runtime.py` | KnowledgeConvergenceRuntime orchestrator |
| `backend/tests/test_knowledge_convergence.py` | 12-scenario validation test suite |
| `docs/UNIGURU_KNOWLEDGE_AUTHORITY_MAP.md` | Authority hierarchy specification across 7 sources |
| `docs/CANONICAL_EVIDENCE_CONTRACT.md` | MDU-compliant schema specification |
| `docs/RETRIEVAL_PROVENANCE.md` | Claim binding & hash protocol specification |
| `docs/KNOWLEDGE_CONVERGENCE_RUNTIME.md` | Architecture specification |
| `docs/REPLAY_VALIDATION.md` | Replay validation protocol specification |
| `REVIEW_PACKET/*` | Handover packet & JSON proofs |

## Modified Files

| File Path | Change Description |
|---|---|
| `backend/kosha/deterministic_pipeline.py` | Integrated convergence runtime, candidate deduplication, and claim-to-evidence bindings |
| `backend/service/uniguru_runtime_api.py` | Added GET `/v2/convergence/authority_map` and POST `/v2/convergence/validate_evidence` endpoints |
