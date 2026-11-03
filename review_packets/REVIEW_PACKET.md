# REVIEW_PACKET.md - UniGuru BHIV Ecosystem Integration

Generated at: `2026-09-05T18:02:56.107005Z`
Status: `ACCEPTED`

## Scope
UniGuru participates in the BHIV execution chain as an internal intelligence capability while exposing only governed, redacted capability output to Mitra.

## Live Evidence
- Vijay integration proof: `review_packets/integration_proof/ecosystem_execution_latest.json` -> `vijay_validation`
- TANTRA integration proof: `review_packets/integration_proof/ecosystem_execution_latest.json` -> `tantra_contract`
- Bucket telemetry evidence: `review_packets/integration_proof/bucket_ecosystem_acceptance_live.json`
- InsightFlow evidence: `review_packets/integration_proof/ecosystem_execution_latest.json` -> `insightflow_observability`
- GC validation evidence: `review_packets/integration_proof/ecosystem_execution_latest.json` -> `gc_validation`
- MDU validation evidence: `review_packets/integration_proof/ecosystem_execution_latest.json` -> `mdu_validation`
- Cross-service replay logs: `review_packets/integration_proof/replay_verification_latest.json`
- API response logs: `review_packets/logs/ecosystem_acceptance_api_responses.json`
- Deployment validation: `review_packets/deployment_proof/ecosystem_deployment_validation.json`

## Runtime Flow
`Mitra/BHIV request -> /runtime/ecosystem/execute -> deterministic Kosha pipeline -> Vijay replay validation -> TANTRA contract -> Bucket telemetry -> InsightFlow observability -> GC authority validation -> MDU schema/provenance validation -> governed response`

## Integration Points
- Internal BHIV: `POST /runtime/ecosystem/execute` returns full integration evidence.
- Replay validation: `POST /runtime/ecosystem/replay` verifies stable runtime, contract, authority and lineage fields.
- Mitra-facing: `POST /mitra/ecosystem/ask` returns answer, verification state, replay status, contract schema and evidence pointers without internal governance payloads.
- Health: `GET /health`, readiness: `GET /ready`, metrics: `GET /metrics`.

## Known Limits
- This workspace run validates local production parity through FastAPI request handling; external BHIV service deployment still needs environment-specific endpoint URLs and credentials.
- Bucket evidence is file-backed unless `UNIGURU_BUCKET_TELEMETRY_ENDPOINT` is configured in deployment.
- Screenshot folders contain evidence notes for API/runtime artifacts; no UI dashboard capture was required for this backend-only convergence run.

---

# UG-HO-02 Knowledge and Retrieval Audit

**Audit date:** 2026-11-03
**Branch:** `ug-ho-02-knowledge-retrieval`
**Status:** Safe remediation and focused validation complete; uncommitted; not deployed.

This dated section supplements the pre-existing packet above. The older `ACCEPTED` status and external-evidence references were not revalidated as part of this audit and are not evidence that the findings below are resolved or that a live service is available.

## Findings and changes

| Finding | Root cause | Action / status |
|---|---|---|
| Sanskrit registry object was mutable through a caller-owned relation list. | Frozen dataclass contained a mutable `List[str]` without defensive normalization. | Fixed with immutable tuple storage and list-compatible serialization; regression added. |
| MasterDB filters could return records outside the requested grade/medium/subject. | Empty filtered candidate list fell back to the entire dataset. | Removed the broad fallback; no-match response shape preserved; positive and negative regression tests added. |
| FAISS authority metadata referenced nonexistent `scripts/rebuild_faiss_index.py`. | Policy metadata was stale relative to the repository. | Updated to `backend/scripts/build_rag_index.py`; corrected scope and canonical-ID claims in `docs/UNIGURU_KNOWLEDGE_AUTHORITY_MAP.md`; path regression added. |
| Test-fixture authority metadata referenced nonexistent `backend/tests/fixtures/`. | Fixtures are inline in test code; there is no separate fixture directory. | Updated the path to `backend/tests/` and added a registry test that verifies all rebuildable paths exist. |
| Unsupported answer sentence inherited evidence from the first unrelated candidate. | Convergence runtime labeled the fallback binding `DERIVED` and reused candidate provenance with no token overlap. | Fixed to explicit `UNVERIFIED_FALLBACK`, `uko:none:unverified`, and zero confidence; regression added. |
| Every MasterDB record fails the validator's source-reference requirement. | The 42 rows have source metadata/hash/page but omit `source_lineage.source_reference`. | Unchanged: authoritative references/signatures cannot be invented. Manifest/validator inconsistency is handed over as a blocker. |
| Uploaded ZIP and checkout differ. | Working branch was created from the existing checkout; the checkout is not a byte-identical ZIP extraction. | Unchanged to avoid overwriting branch/source data. See the baseline for comparison counts and behavior-sensitive examples. |

## Validation

- Baseline: **139 passed**.
- Final focused post-remediation suite: **232 passed, 1 skipped**. The skip is `backend/tests/test_rag_health.py`, whose guard reports that a generated FAISS index is not committed.
- Separate targeted claim-binding check: **3 passed**.
- MasterDB validator: **0/42 valid**, all missing `source_reference`; duplicates: 0; canonical authority: false.
- MasterDB coverage: **4/160 cells (2.5%)**.
- Current-checkout read-only RAG probe: healthy local generated index (75 docs/160 chunks), but not present in the uploaded ZIP.
- No live external integration, index rebuild, deployment, commit, or push was performed.

The exact commands and interpretation are in `../docs/handover/RETRIEVAL_VALIDATION_MATRIX.md`.

## Changed and created files

**Modified**

- `backend/convergence/authority_contract.py`
- `backend/convergence/convergence_runtime.py`
- `backend/ontology/sanskrit/schema.py`
- `backend/tests/test_knowledge_convergence.py`
- `backend/tests/test_phase2_knowledge_convergence_trust_validation.py`
- `docs/UNIGURU_KNOWLEDGE_AUTHORITY_MAP.md`
- `retrieval/retrieval_engine.py`
- `review_packets/REVIEW_PACKET.md`

**Created**

- `backend/tests/test_sanskrit_schema_immutability.py`
- `tests/test_masterdb_retrieval_filters.py`
- `docs/handover/KNOWLEDGE_AND_RETRIEVAL_BASELINE.md`
- `docs/handover/KNOWLEDGE_SOURCE_INVENTORY.md`
- `docs/handover/RETRIEVAL_VALIDATION_MATRIX.md`
- `docs/handover/KNOWLEDGE_CONVERGENCE_MAP.md`
- `docs/handover/KNOWN_KNOWLEDGE_GAPS.md`

No source dataset or generated index was modified.

## Next-build tasks

### 1. Close MasterDB provenance and authority gaps — 300 minutes

**Objective:** Reconcile each canonical record with an authoritative Balbharti source reference, determine the correct provenance-status/manifest policy, and report actual curriculum coverage without promoting samples.

**Dependencies:** Vijay/MDU must provide or identify the licensed/authoritative textbook artifacts and citation format, confirm source-reference semantics, and approve how signatures/manifests are regenerated.

**Acceptance criteria:**

- Every canonical row has a resolvable source reference, edition, page, and verifiable source hash, or is explicitly quarantined from canonical retrieval.
- Validator status, manifest status, and authority map no longer contradict each other.
- Coverage report names the missing grade/subject/medium cells; no catalog-only entry is counted as answer content.
- Existing record IDs and source data are preserved; no unsigned data rewrite is accepted.

**Reproducible tests:**

```powershell
python -m pytest -q -p no:cacheprovider --basetemp="$env:TEMP\ug-ho-02-masterdb-tests" tests/test_curriculum_truth_validation.py
python -c "import json;from pathlib import Path;from masterdb.masterdb_validation import validate_masterdb;r=json.loads(Path('masterdb/balbharti/canonical_dataset.json').read_text(encoding='utf-8'));v=validate_masterdb(r);assert v['valid_record_count']==len(r) and not v['duplicate_record_ids'];print(v['record_count'],v['valid_record_count'])"
```

### 2. Complete source identity and claim-evidence convergence — 270 minutes

**Objective:** Confirm whether `AKASHIC` and `KOSHA_JSON` are distinct source identities or aliases, document one physical lineage for the shared records, and ensure every runtime answer sentence is bound only to supporting evidence.

**Dependencies:** Vijay/MDU source-identity decision; accepted token/semantic evidence matching policy; confirmation of whether `retrieval/knowledge_convergence.py` is intended to be activated.

**Acceptance criteria:**

- Authority-map entries resolve to physical paths, owners, and stable source identifiers without duplicating records.
- No unmatched sentence is marked `VERIFIED`/`DERIVED` or assigned unrelated canonical provenance.
- If the curriculum helper is activated, it emits sentence-level claim bindings or an explicitly unverified result, with replay-stable hashes.
- Existing runtime response shapes and source keys remain compatible unless approved.

**Reproducible tests:**

```powershell
python -m pytest -q -p no:cacheprovider --basetemp="$env:TEMP\ug-ho-02-convergence-tests" backend/tests/test_knowledge_convergence.py backend/tests/test_phase2_knowledge_convergence_trust_validation.py backend/tests/test_sanskrit_schema_immutability.py
```

Add a regression asserting that an answer with one evidence-backed sentence and one unrelated sentence yields one verified binding and one explicit unverified binding.

### 3. Reconcile archive parity and validate the index lifecycle in isolation — 360 minutes

**Objective:** Align the task branch with the approved ZIP revision without overwriting existing branch work, establish the supported retrieval entrypoint, and validate index build/activation in a disposable root.

**Dependencies:** Vijay confirms the intended source revision and Unified RAG behavior; the required embedding packages/model are available offline or approved; index pointer/output paths can be redirected in test configuration; deployment credentials are not required for local validation.

**Acceptance criteria:**

- A manifest identifies archive-only, checkout-only, and changed files; behavior-sensitive differences are resolved or explicitly accepted.
- A temporary index build validates source-manifest hash, DB/index chunk parity, and runtime health without changing the working `backend/RAG/active_index.json`.
- Candidate evidence resolves to documented source identity; unsupported/unavailable index behavior is explicit.
- Archive-specific and checkout-specific retrieval tests pass; no deployment or external integration is claimed without live evidence.

**Reproducible tests:**

```powershell
python -m pytest -q -p no:cacheprovider --basetemp="$env:TEMP\ug-ho-02-rag-tests" backend/tests/test_rag_health.py backend/tests/test_retriever_quality.py
python backend/scripts/build_rag_index.py --help
```

Add an isolated lifecycle test with monkeypatched `RAG_ROOT` and temporary output paths before invoking `build_index`; assert the existing active pointer is unchanged. Do not run the builder against the shared/default RAG root as part of this task.

## Handover status

All six requested documents are present. Five confirmed registry, retrieval, and provenance defects received focused regression coverage. MasterDB provenance completion, source-coverage expansion, archive parity, portable index generation, and live Vijay/BHIV integration remain open; the latter may require Vijay's access and participation. Work remains uncommitted and undeployed on `ug-ho-02-knowledge-retrieval`.

---

# T-GOV-F01 — TANTRA Schema Violation Remediation

**Date:** 2026-11-03

> Historical pre-integration snapshot. The route and security findings below describe the state before the active-bridge continuation documented at the end of this packet; that later section supersedes claims that the bridge was untouched or the schema module was unavailable.

## Root cause

The bridge (`backend/bridge/server.py`) accepted and returned untyped `Dict[str, Any]` payloads. No Pydantic validation existed on inbound requests or outbound responses. `backend/contracts/` contained only a JSON file with no Python schema module. The forbidden pattern `bypass_governance` could appear in any field without detection. `enforcement_signature` was not validated as a 64-character hex SHA-256.

## Remediation

| Deliverable | File | Status |
|---|---|---|
| Schema contracts (Pydantic v2) | `backend/contracts/schemas.py` | Created |
| Architecture Decision Record | `docs/ADR-T-GOV-F01.md` | Created |
| Bridge schema unit + negative tests | `backend/tests/unit/test_bridge_schemas.py` | Created |
| TANTRA PKB pinned dependencies | `backend/requirements.tantra.txt` | Created |

## Schema models

- `BridgeChatRequest` — inbound, `extra="forbid"`, rejects `bypass_governance` in caller/source/context keys, requires at least one query field.
- `BridgeChatResponse` — outbound, validates `enforcement_signature` as 64-char lowercase hex, `Literal` types on all discriminator fields.
- `VerificationBlock`, `BridgeResponseData` — nested outbound.
- `HealthResponse` — `GET /health` outbound.
- `AuditEventSchema` — governance audit event, `extra="forbid"`, rejects control characters.

## Test coverage

`backend/tests/unit/test_bridge_schemas.py` covers:
- Valid payloads for all models.
- Missing query field (negative).
- `bypass_governance` in caller, source, context keys, case-insensitive (negative).
- Extra fields rejected (negative).
- Oversized fields rejected (negative).
- Bad signature format: short, non-hex, uppercase (negative).
- Bad `Literal` values for decision/status_action/verification_status/outcome (negative).
- `EnforcementSealer` determinism (50-run gate), tamper detection.
- `SovereignEnforcement` VERIFIED/PARTIAL/UNVERIFIED paths, seal integrity, tampered content detection.

Existing suites (`test_jwt_rs256.py`, `test_replay_table.py`, `test_audit_emitter.py`, `test_rbac_audit_integration.py`) already cover the security stack and the 50-run determinism gate.

## Verification commands

```powershell
# Schema import check (no server required)
python -c "from contracts.schemas import BridgeChatRequest, BridgeChatResponse; print('schemas OK')"

# Schema unit + negative tests
python -m pytest -q backend/tests/unit/test_bridge_schemas.py

# Full security + determinism suite
python -m pytest -q backend/tests/unit/ backend/tests/integration/
```

## Boundaries respected

- `backend/bridge/server.py` was not modified (Vijay's runtime contract).
- No source dataset, generated index, or shared infrastructure was changed.
- `backend/requirements.txt` was not overwritten; TANTRA-pinned deps are in `requirements.tantra.txt`.

---

# UG-HO-02 Continuation — Final Handover Assessment

**Updated:** 2026-11-03 (continuation pass)

## Resolved blockers

| Blocker | Resolution |
|---|---|
| Sanskrit registry mutation through caller-owned list | Fixed: tuple storage, list-compatible serialization, regression test. |
| MasterDB filter fall-through returning out-of-scope records | Fixed: broad fallback removed, positive/negative regression tests. |
| FAISS authority-map rebuild path pointed to nonexistent script | Fixed: updated to `backend/scripts/build_rag_index.py`, scope corrected. |
| Test-fixture authority path pointed to nonexistent directory | Fixed: updated to `backend/tests/`. |
| Unsupported answer sentence falsely bound to unrelated evidence | Fixed: `UNVERIFIED_FALLBACK`, zero confidence, no canonical object. |
| Root cause of 42/42 provenance failures documented | Confirmed: `source_reference` key was never populated by ingestion script. |
| 4/160 coverage gap fully documented | Confirmed: 4 present cells listed; 156 missing cells categorised by grade/subject/medium. |
| FAISS active-pointer protection procedure documented | Confirmed: `--output-root` does not protect pointer; monkeypatch procedure written. |
| ZIP vs checkout parity report produced | Confirmed: file-by-file structural diff completed; behavior-sensitive differences identified. |
| Live integration checklist prepared for Vijay/BHIV | Confirmed: 7-section checklist written in `KNOWLEDGE_AND_RETRIEVAL_BASELINE.md`. |

## Remaining blockers

| Blocker | Owner | Unblocking action |
|---|---|---|
| `source_reference` absent from all 42 MasterDB records | Vijay/MDU | Approve citation format and migration script. |
| `canonical_dataset_manifest.json` contradicts validator | Vijay/MDU | Regenerate manifest from validator output after migration. |
| Curriculum coverage 4/160 (2.5%) | Vijay/MDU | Confirm in-scope grades/subjects/mediums; ingest additional records through validated pipeline. |
| `/chat` had no active contract/auth/replay/audit binding | Resolved in the active-bridge continuation below | Route-level OpenAPI and security tests now cover the wiring. |
| Archive-only capabilities not in checkout | Vijay | Confirm merge base; forward-port or rebase. |
| FAISS index not generated or validated | Isha (after Vijay confirms embedding deps) | Run safe isolated build procedure. |
| Live BHIV/Vijay service integration not verified | Vijay | Provide endpoint URLs and credentials. |
| `requirements.txt` TANTRA PKB pinning not verified | Isha | Verify after `contracts/schemas.py` spec is received. |

## Exact files changed (this audit, both passes)

**Modified:**
- `backend/convergence/authority_contract.py`
- `backend/convergence/convergence_runtime.py`
- `backend/ontology/sanskrit/schema.py`
- `backend/tests/test_knowledge_convergence.py`
- `backend/tests/test_phase2_knowledge_convergence_trust_validation.py`
- `docs/UNIGURU_KNOWLEDGE_AUTHORITY_MAP.md`
- `retrieval/retrieval_engine.py`
- `review_packets/REVIEW_PACKET.md` (this file)
- `docs/handover/KNOWLEDGE_AND_RETRIEVAL_BASELINE.md`
- `docs/handover/KNOWN_KNOWLEDGE_GAPS.md`
- `docs/handover/RETRIEVAL_VALIDATION_MATRIX.md`

**Created:**
- `backend/tests/test_sanskrit_schema_immutability.py`
- `tests/test_masterdb_retrieval_filters.py`
- `docs/handover/KNOWLEDGE_SOURCE_INVENTORY.md`
- `docs/handover/KNOWLEDGE_CONVERGENCE_MAP.md`

No source dataset, generated index, shared infrastructure, or Vijay's runtime was modified.

## Actual test results

| Suite | Command | Result |
|---|---|---|
| Baseline (pre-remediation) | Focused 7-file suite | 139 passed |
| Post-remediation focused suite | 13-file suite (see RETRIEVAL_VALIDATION_MATRIX.md) | 232 passed, 1 skipped |
| MasterDB validator | `validate_masterdb` on 42 records | 0/42 valid; all missing `source_reference`; 0 duplicate IDs |
| Coverage validator | `build_coverage_report` on 42 records | 4/160 cells (2.5%) |
| RAG health probe (read-only) | `get_rag_health()` | Healthy local index (75 docs, 160 chunks, 384 dims); not in ZIP |
| FAISS index build | Not executed | Embedding deps not confirmed; active pointer protection requires monkeypatch |
| Live BHIV integration | Not executed | No credentials or endpoint URLs available |

## Evidence required from Vijay

1. Authoritative `source_reference` citation format for Balbharti records.
2. Confirmation that ISBNs `978-81-7657-001-2` through `978-81-7657-004-3` are licensed for ingestion.
3. Approval of the `source_reference` migration script before execution.
4. Intended merge base: checkout branch or ZIP revision.
5. Whether `backend/retrieval/balbharati/` and `uniguru_sanskrit_decoder/` are required for the current release.
6. `contracts/schemas.py` Pydantic schema specification (TANTRA requirement).
7. Deployment endpoint URLs and credentials for live BHIV integration verification.
8. Confirmation that `faiss` and `sentence-transformers` are available in the deployment environment.

## Final handover readiness assessment

| Dimension | Status | Notes |
|---|---|---|
| Knowledge inventory | COMPLETE | All sources, readers, and authority labels documented. |
| Retrieval validation | PARTIALLY VERIFIED | 232 tests pass on checkout; archive-only retrieval paths (Balbharati hybrid, Sanskrit decoder dispatch) not tested. |
| Provenance | PARTIALLY VERIFIED | Root cause confirmed; fix requires Vijay/MDU approval and data migration. |
| Canonical-source integration | PARTIALLY VERIFIED | Kosha/AKASHIC/Markdown paths verified; MasterDB authority gate blocked on `source_reference`. |
| Graph validation | PARTIALLY VERIFIED | Sanskrit decoder graph and ontology snapshot graph tested; curriculum graph depends on MasterDB provenance. |
| Repository handover | BLOCKED | Merge base unconfirmed; live integration unverified. |
| Next build ready | YES | Three bounded tasks defined; all have clear acceptance criteria and reproducible test commands. |

---

# T-GOV-F01 — Active Bridge Integration Continuation

**Updated:** 2026-11-03
**Status:** Implemented and tested locally; deployment/runtime configuration remains unverified.
**Branch:** `ug-ho-02-knowledge-retrieval`; no commit, push, merge, or deployment.

## Root cause and active-route evidence

The schema module and unit tests existed in the working tree, but `/chat` still accepted a separate permissive `ChatRequest` and had no response model or security dependency. The contract-only tests therefore did not exercise active FastAPI behavior.

- `backend/bridge/server.py` now declares `BridgeChatRequest` as the route body and `BridgeChatResponse` as its response model.
- OpenAPI now references `#/components/schemas/BridgeChatRequest` for the request body and `#/components/schemas/BridgeChatResponse` for the 200 response; its security requirement is `HTTPBearer`.
- Route tests confirm unknown fields, caller/source/query injection, and nested context key/value injection return 422 before engine evaluation.
- Route tests confirm invalid/missing authentication and unconfigured JWT keys fail closed; an invalid response object is rejected by FastAPI rather than returned.
- The forbidden marker check is targeted to `bypass_governance`; arbitrary ordinary query/context text remains valid.

## Security lifecycle

For `/chat`, the active order is RS256 JWT verification, existing RBAC allowlist, single-use `jti` consumption, then bridge business processing. Missing authentication is 401, disallowed roles are 403, replay is 409, missing JWT configuration is 503, and replay-store write failure is 503. Audit middleware emits hash-chained ALLOW/DENY events for completed and rejected route requests, including request-validation failures. It does not record bearer tokens or request text.

Replay and audit persistence read errors now fail closed; they are no longer treated as empty stores. The replay table only coordinates threads within one process. It is not safe for multi-worker or multi-host replay exclusion without a shared atomic store.

Audit-log loading now also verifies each stored entry hash against its contents, including a single-entry log. Corrupt or tampered audit state fails closed.

## Transport policy

The default engine target remains `http://127.0.0.1:8000/ask`; that HTTP URL is rejected for forwarding by default. Local HTTP is enabled only with both `UNIGURU_ENV=development` and `UNIGURU_ALLOW_LOCAL_HTTP=true`, and only for localhost/loopback targets. HTTPS forwarding is accepted. No deployment configuration or live HTTPS endpoint was inspected, so production HTTPS remains an operational prerequisite, not a verified integration.

## Validation evidence

| Validation | Command / evidence | Result |
|---|---|---|
| Active route, schema, auth, replay, audit, transport, 50-run response test, and related component tests | From `backend`: `python -m pytest -q -p no:cacheprovider --basetemp="$env:TEMP\tgov-route-tests-final3" tests\integration\test_bridge_route_governance.py tests\unit\test_bridge_schemas.py tests\unit\test_replay_table.py tests\unit\test_audit_emitter.py tests\unit\test_jwt_rs256.py` | **103 passed** |
| All backend unit and integration suites | From `backend`: `python -m pytest -q -p no:cacheprovider --basetemp="$env:TEMP\tgov-handover-final" tests\unit tests\integration` | **111 passed** |
| End-to-end determinism | Same JSON request body, 50 FastAPI requests, controlled engine/trace/clock, fresh signed `jti` values; hashes of full serialized HTTP responses | **50/50 identical response hashes** |
| Syntax and whitespace | `py_compile` on changed Python modules; `git diff --check` | Passed |

The 50-run result is a controlled end-to-end HTTP response check, not a claim that real-time IDs, audit timestamps, external engine responses, or production runs are intrinsically deterministic.

## Files changed or created in this continuation

**Modified:** `backend/bridge/server.py`, `backend/contracts/schemas.py`, `backend/security/audit_emitter.py`, `backend/security/replay_table.py`, `backend/tests/unit/test_audit_emitter.py`, `backend/tests/unit/test_replay_table.py`, `docs/ADR-T-GOV-F01.md`, and this packet.

**Created:** `backend/tests/integration/test_bridge_route_governance.py`.

The previously submitted `backend/tests/unit/test_bridge_schemas.py` and `backend/requirements.tantra.txt` were preserved. Other pre-existing UG-HO-02 worktree changes are listed in the earlier handover sections.

## Remaining blockers

- Configure and verify the production RS256 public key, token issuer/audience policy if required, and HTTPS `UNIGURU_ENGINE_URL`; no live service configuration was available.
- Replace or constrain the file-backed replay table before deploying multiple worker processes/hosts.
- Existing external integrations and deployment behavior were not exercised. This continuation does not claim T-GOV-F01 production acceptance.

---

# UG-HO-02 / T-GOV-F01 — Final Worktree and Production Handover

**Verified:** 2026-11-03
**Branch:** `ug-ho-02-knowledge-retrieval`
**HEAD:** `b553139618729bf30624d59e635a61f222863853`
**Repository state:** all task changes remain uncommitted; no deletions; no deployment. The existing branch and worktree were preserved.

## Final status by evidence class

| Class | Status and evidence |
|---|---|
| Locally implemented and tested | UG-HO-02 fixes and documentation remain present. T-GOV-F01 route models, OpenAPI request/response binding, RS256/RBAC, single-process replay enforcement, request auditing, transport guard, and fail-closed persistence/audit verification are covered by local tests. |
| Awaiting Vijay/BHIV approval | Confirm accepted response contract/extra-field policy, permitted JWT roles and issuer/audience requirements, service topology, shared-store technology/ownership, audit-retention policy, and dependency baseline for deployment. These decisions are not implemented as infrastructure changes. |
| Requiring production configuration | Provide the RS256 public-key configuration, HTTPS engine endpoint, storage paths/permissions, and appropriate replay-store configuration via the approved deployment secret/configuration manager. Configure production flags to disallow local HTTP. Never provide signing private keys or bearer tokens in this repository or handover packet. |
| Not yet verified | No deployment key, endpoint URL, certificate, production runtime, multi-replica behavior, external BHIV/Vijay service, or production dependency resolution was inspected or tested. No production acceptance is claimed. |

## Production acceptance checklist for Vijay/BHIV

Complete each item with deployment evidence in the authorized system; do not attach secret values to this repository or packet.

| Check | Owner | Acceptance evidence required | State |
|---|---|---|---|
| Configure RS256 verification key through `UNIGURU_JWT_PUBLIC_KEY` or `UNIGURU_JWT_PUBLIC_KEY_PATH`; keep signing private key with issuer only. | Vijay/BHIV deployment owner | Key fingerprint/source and successful valid/invalid-token smoke tests, recorded without key material. | Not verified |
| Confirm issuer and audience policy; configure `UNIGURU_JWT_ISSUER` and `UNIGURU_JWT_AUDIENCE` where required. | Vijay/BHIV identity owner | Approved claim contract and staging tests for matching and mismatched claims. | Approval/configuration pending |
| Approve role allowlist currently present in bridge configuration. | Vijay/BHIV product/security owner | Written role-to-caller authorization decision and allow/deny test evidence. | Approval pending |
| Set `UNIGURU_ENGINE_URL` to the actual HTTPS endpoint; validate DNS, reachability, certificate chain/hostname, and downstream auth requirements in the deployed environment. | Vijay/BHIV runtime owner | Redacted configuration reference plus successful staging connection and failure-path test; do not record credentials. | Not verified |
| Set production mode and ensure local HTTP override is disabled. | Vijay/BHIV deployment owner | Deployment policy/config review proving production does not set `UNIGURU_ALLOW_LOCAL_HTTP=true`; no loopback HTTP forwarding. | Not verified |
| Decide whether deployment has multiple workers/replicas. If yes, approve a shared atomic replay backend with insert-if-absent/compare-and-set and expiry aligned with token expiration/leeway. | Vijay/BHIV infrastructure/security owner | Architecture approval and concurrent duplicate-token integration test across separate workers. | Blocker before multi-worker production |
| For a single-process deployment only, configure durable, access-controlled `UNIGURU_REPLAY_STORE_PATH`; verify restart persistence and fail-closed behavior. | Vijay/BHIV deployment owner | Staging restart/replay test and permissions check. | Not verified |
| Configure durable `UNIGURU_BRIDGE_AUDIT_PATH`; approve retention, access, chain verification, alerting, and chain-aware archival/rotation. | Vijay/BHIV security/operations owner | Audit-chain verification and tamper/append-failure handling evidence under staging permissions. | Not verified |
| Reconcile the strict `requirements.tantra.txt` pins with the production runtime manifest and approved lock/resolution process. | Vijay/BHIV release owner | Clean environment install and full relevant test run against the exact release dependency set. | Not verified |
| Run authorized end-to-end staging acceptance for `/chat`, including 422 schema rejection, 401/403 auth, 409 replay, audit entries, HTTPS forwarding, and valid response serialization. | Vijay/BHIV service owner | Test run against the candidate deployment; sanitized results and deployment revision. | Not run |
| Approve deploy/release and retain rollback plan. | Vijay/BHIV release owner | Explicit change approval and release evidence. | Not approved / not deployed |

**Configuration names (no values):** `UNIGURU_JWT_PUBLIC_KEY`, `UNIGURU_JWT_PUBLIC_KEY_PATH`, `UNIGURU_JWT_ISSUER`, `UNIGURU_JWT_AUDIENCE`, `UNIGURU_ENGINE_URL`, `UNIGURU_ENV`, `UNIGURU_ALLOW_LOCAL_HTTP`, `UNIGURU_REPLAY_STORE_PATH`, and `UNIGURU_BRIDGE_AUDIT_PATH`.

The current replay JSON file and process-local lock do not provide cross-worker atomicity. A shared Redis/database implementation is a recommendation only; selection and implementation require Vijay/BHIV approval and are outside this handover change.

## Complete worktree inventory

Inventory as observed on the branch above. “Modified” denotes files differing from HEAD; “untracked” denotes files present in the worktree but not tracked at HEAD. Existing untracked submissions are intentionally retained. The categories identify task ownership, not staging/commit status.

### Modified files — 13

**UG-HO-02**

- `backend/convergence/authority_contract.py`
- `backend/convergence/convergence_runtime.py`
- `backend/ontology/sanskrit/schema.py`
- `backend/tests/test_knowledge_convergence.py`
- `backend/tests/test_phase2_knowledge_convergence_trust_validation.py`
- `docs/UNIGURU_KNOWLEDGE_AUTHORITY_MAP.md`
- `retrieval/retrieval_engine.py`

**T-GOV-F01**

- `backend/bridge/server.py`
- `backend/security/audit_emitter.py`
- `backend/security/replay_table.py`
- `backend/tests/unit/test_audit_emitter.py`
- `backend/tests/unit/test_replay_table.py`

**Both handovers**

- `review_packets/REVIEW_PACKET.md`

### Untracked files retained in the worktree — 12

**T-GOV-F01**

- `backend/contracts/schemas.py`
- `backend/requirements.tantra.txt`
- `backend/tests/integration/test_bridge_route_governance.py`
- `backend/tests/unit/test_bridge_schemas.py`
- `docs/ADR-T-GOV-F01.md`

**UG-HO-02**

- `backend/tests/test_sanskrit_schema_immutability.py`
- `docs/handover/KNOWLEDGE_AND_RETRIEVAL_BASELINE.md`
- `docs/handover/KNOWLEDGE_CONVERGENCE_MAP.md`
- `docs/handover/KNOWLEDGE_SOURCE_INVENTORY.md`
- `docs/handover/KNOWN_KNOWLEDGE_GAPS.md`
- `docs/handover/RETRIEVAL_VALIDATION_MATRIX.md`
- `tests/test_masterdb_retrieval_filters.py`

No files were deleted. No source data, generated retrieval index, production configuration, or shared infrastructure was changed.

## Reproducible final verification

From `backend`:

```powershell
python -m pytest -q -p no:cacheprovider --basetemp="$env:TEMP\tgov-route-tests-final3" tests\integration\test_bridge_route_governance.py tests\unit\test_bridge_schemas.py tests\unit\test_replay_table.py tests\unit\test_audit_emitter.py tests\unit\test_jwt_rs256.py
python -m pytest -q -p no:cacheprovider --basetemp="$env:TEMP\tgov-handover-final" tests\unit tests\integration
```

Observed results: **103 passed** in the focused bridge/security selection; **111 passed** in all backend unit and integration suites. The route-level controlled 50-request test produced **50/50 identical full response hashes**. Final `git diff --check` was clean. These results establish local test behavior only.

## Documentation secret/configuration review

The T-GOV-F01 ADR and this packet were scanned for private-key blocks, populated `UNIGURU_*` assignments, bearer-token values, and common GitHub-token patterns; none were found. Documentation names configuration variables only and includes no key material, credentials, or deployment endpoint value. This check is limited to the reviewed documentation files, not a repository-wide secret scan.

## Exact remaining blockers and owners

1. **Vijay/BHIV identity/security:** approve JWT role allowlist and issuer/audience requirements; supply production key configuration through approved secret/configuration management, without transferring a signing private key.
2. **Vijay/BHIV runtime/deployment:** provide and verify the production HTTPS engine endpoint, TLS trust/reachability, downstream auth, and production flags.
3. **Vijay/BHIV infrastructure/security:** confirm worker/replica topology and approve a shared atomic replay store if more than one process/replica will serve requests; no such infrastructure has been introduced.
4. **Vijay/BHIV operations/security:** approve durable audit storage, permissions, retention, integrity monitoring, and chain-aware archival.
5. **Vijay/BHIV release owner:** reconcile the TANTRA pinned test manifest with the production dependency baseline and authorize staging/release acceptance. No deployment approval was given.
6. **UG-HO-02 owners (Vijay/MDU and repository owner):** resolve MasterDB source references/manifest, archive-versus-checkout revision, curriculum coverage, and external integration evidence as documented above.

**Handover disposition:** local remediation and tests are complete for the bounded branch changes; production readiness remains **blocked pending the checklist and owner approvals**. No production acceptance, deployment, commit, push, or merge is claimed.
