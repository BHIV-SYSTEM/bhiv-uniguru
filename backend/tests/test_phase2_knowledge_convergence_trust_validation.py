"""
Phase 2: Advanced Integration & Security Hardening
Isha Singh — UniGuru Knowledge Convergence and Trust Validation

Unit test coverage for:
- Production monitoring (authority map observability, convergence metrics)
- Error boundary safety (empty candidates, malformed input, fallback isolation)
- E2E integration verification (full pipeline, API contract, proof emission)
- API contract boundaries (authority map, validate_evidence endpoint)
- Deterministic execution (replay ID stability, provenance hash chain, index rebuild)
- Trust validation (authority tier enforcement, claim binding verification status)
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("UNIGURU_API_AUTH_REQUIRED", "false")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def runtime():
    from convergence.convergence_runtime import KnowledgeConvergenceRuntime
    return KnowledgeConvergenceRuntime()


@pytest.fixture(scope="module")
def client():
    from service.uniguru_runtime_api import app
    return TestClient(app)


def _canonical_candidates() -> List[Dict[str, Any]]:
    return [
        {"content": "Dharma is the sustaining order of life and duty.", "source": "MASTERDB", "concept": "dharma", "confidence": 0.92},
        {"content": "Dharma governs cosmic and moral conduct.", "source": "AKASHIC", "concept": "dharma", "confidence": 0.88},
    ]


def _fallback_candidates() -> List[Dict[str, Any]]:
    return [
        {"content": "Unverified LLM draft text.", "source": "LLM_FALLBACK", "concept": "unverified", "authority_tier": "FALLBACK"},
    ]


# ---------------------------------------------------------------------------
# 1. Production Monitoring — authority map and convergence observability
# ---------------------------------------------------------------------------

def test_authority_map_exposes_all_required_source_keys():
    from convergence.authority_contract import get_authority_map
    amap = get_authority_map()
    d = amap.to_dict()
    for key in ("MASTERDB", "AKASHIC", "KNOWLEDGE_GRAPH", "KOSHA_JSON", "MARKDOWN_CORPUS", "FAISS_VECTOR_INDEX", "LLM_FALLBACK", "TEST_FIXTURE"):
        assert key in d, f"Missing source key: {key}"


def test_authority_map_tier_classifications_are_correct():
    from convergence.authority_contract import get_authority_map, AuthorityTier
    amap = get_authority_map()
    assert amap.get_tier("MASTERDB") == AuthorityTier.CANONICAL
    assert amap.get_tier("AKASHIC") == AuthorityTier.CANONICAL
    assert amap.get_tier("FAISS_VECTOR_INDEX") == AuthorityTier.DERIVED
    assert amap.get_tier("LLM_FALLBACK") == AuthorityTier.FALLBACK
    assert amap.get_tier("TEST_FIXTURE") == AuthorityTier.TEST_FIXTURE


def test_faiss_authority_map_rebuild_path_points_to_existing_builder():
    from pathlib import Path

    from convergence.authority_contract import get_authority_map

    source = get_authority_map().get_source("FAISS_VECTOR_INDEX")
    builder_path = Path(__file__).resolve().parents[2] / source.rebuild_path

    assert source.rebuildable is True
    assert builder_path.is_file()


def test_rebuildable_authority_sources_have_existing_paths():
    from pathlib import Path

    from convergence.authority_contract import get_authority_map

    repository_root = Path(__file__).resolve().parents[2]
    for source in get_authority_map().to_dict().values():
        if source["rebuildable"]:
            assert (repository_root / source["rebuild_path"]).exists(), source["source_key"]


def test_authority_map_unknown_source_defaults_to_fallback():
    from convergence.authority_contract import get_authority_map, AuthorityTier
    amap = get_authority_map()
    assert amap.get_tier("NONEXISTENT_SOURCE_XYZ") == AuthorityTier.FALLBACK


def test_retrieval_run_record_exposes_candidate_and_dedup_counts(runtime):
    record, deduped = runtime.process_query_run(
        query="What is dharma?",
        candidates=_canonical_candidates(),
        synthesized_answer="Dharma is the sustaining order of life and duty.",
    )
    assert record.candidate_count == 2
    assert record.deduplicated_candidate_count == 2
    assert len(deduped) == 2


def test_retrieval_run_record_exposes_index_version(runtime):
    record, _ = runtime.process_query_run(
        query="What is karma?",
        candidates=_canonical_candidates(),
        synthesized_answer="Dharma is the sustaining order of life and duty.",
    )
    assert record.index_version == "UNIGURU_CONVERGENCE_INDEX_V1"


def test_convergence_record_to_dict_is_serialisable(runtime):
    import json
    record, _ = runtime.process_query_run(
        query="What is dharma?",
        candidates=_canonical_candidates(),
        synthesized_answer="Dharma is the sustaining order of life and duty.",
    )
    d = record.to_dict()
    serialised = json.dumps(d)
    assert "query_id" in serialised
    assert "replay_id" in serialised
    assert "verification_status" in serialised


# ---------------------------------------------------------------------------
# 2. Error Boundary Safety
# ---------------------------------------------------------------------------

def test_empty_candidates_produces_no_verified_knowledge_status(runtime):
    record, deduped = runtime.process_query_run(
        query="What is the stock price of Apple?",
        candidates=[],
        synthesized_answer="I do not have verified knowledge to answer this question.",
    )
    assert record.verification_status == "NO_VERIFIED_KNOWLEDGE"
    assert record.candidate_count == 0
    assert deduped == []


def test_empty_candidates_produces_unverified_fallback_binding(runtime):
    from convergence.retrieval_evidence_contract import ClaimVerificationStatus
    record, _ = runtime.process_query_run(
        query="Unknown topic",
        candidates=[],
        synthesized_answer="I do not have verified knowledge to answer this question.",
    )
    assert len(record.claim_bindings) == 1
    assert record.claim_bindings[0].verification_status == ClaimVerificationStatus.UNVERIFIED_FALLBACK
    assert record.claim_bindings[0].confidence == 0.0


def test_fallback_source_is_isolated_from_canonical_tier(runtime):
    from convergence.authority_contract import AuthorityTier
    record, _ = runtime.process_query_run(
        query="Speculative topic",
        candidates=_fallback_candidates(),
        synthesized_answer="Unverified LLM draft text.",
    )
    assert record.selected_evidence[0].authority_tier == AuthorityTier.FALLBACK


def test_duplicate_candidates_do_not_inflate_evidence_count(runtime):
    dupes = [
        {"content": "Karma is the causal continuity of action.", "source": "MASTERDB", "concept": "karma"},
        {"content": "Karma is the causal continuity of action.", "source": "AKASHIC", "concept": "karma"},
        {"content": "Karma is the causal continuity of action.", "source": "KOSHA", "concept": "karma"},
    ]
    record, deduped = runtime.process_query_run(
        query="What is karma?",
        candidates=dupes,
        synthesized_answer="Karma is the causal continuity of action.",
    )
    assert record.candidate_count == 3
    assert record.deduplicated_candidate_count == 1
    assert len(deduped) == 1


def test_whitespace_only_content_is_excluded_from_evidence(runtime):
    candidates = [
        {"content": "   ", "source": "MASTERDB", "concept": "empty"},
        {"content": "Dharma is duty.", "source": "MASTERDB", "concept": "dharma"},
    ]
    record, deduped = runtime.process_query_run(
        query="What is dharma?",
        candidates=candidates,
        synthesized_answer="Dharma is duty.",
    )
    assert record.deduplicated_candidate_count == 1
    assert all(e.text_span.strip() for e in record.selected_evidence)


def test_validate_evidence_api_rejects_missing_query(client):
    resp = client.post(
        "/v2/convergence/validate_evidence",
        json={"synthesized_answer": "Some answer.", "candidates": []},
    )
    assert resp.status_code == 422


def test_validate_evidence_api_rejects_missing_answer(client):
    resp = client.post(
        "/v2/convergence/validate_evidence",
        json={"query": "What is dharma?", "candidates": []},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 3. E2E Integration Verification
# ---------------------------------------------------------------------------

def test_full_convergence_pipeline_returns_verified_status():
    from convergence.convergence_runtime import run_convergence_pipeline
    record, deduped = run_convergence_pipeline(
        query="What is dharma?",
        candidates=_canonical_candidates(),
        synthesized_answer="Dharma is the sustaining order of life and duty.",
        trace_id="phase2_e2e_convergence",
    )
    assert record.verification_status == "VERIFIED"
    assert record.replay_safe is True
    assert len(record.selected_evidence) > 0
    assert len(record.claim_bindings) > 0


def test_full_convergence_pipeline_binds_claims_to_canonical_evidence():
    from convergence.convergence_runtime import run_convergence_pipeline
    from convergence.retrieval_evidence_contract import ClaimVerificationStatus
    record, _ = run_convergence_pipeline(
        query="What is dharma?",
        candidates=_canonical_candidates(),
        synthesized_answer="Dharma is the sustaining order of life and duty.",
        trace_id="phase2_claim_binding",
    )
    statuses = {cb.verification_status for cb in record.claim_bindings}
    assert ClaimVerificationStatus.VERIFIED in statuses


def test_api_validate_evidence_returns_valid_true_for_canonical_candidates(client):
    resp = client.post(
        "/v2/convergence/validate_evidence",
        json={
            "query": "What is dharma?",
            "synthesized_answer": "Dharma is the sustaining order of life and duty.",
            "candidates": [
                {"content": "Dharma is the sustaining order of life and duty.", "source": "MASTERDB", "concept": "dharma"}
            ],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True
    assert body["retrieval_run_record"]["deduplicated_candidate_count"] == 1
    assert body["retrieval_run_record"]["replay_safe"] is True


def test_api_validate_evidence_returns_valid_false_for_empty_candidates(client):
    resp = client.post(
        "/v2/convergence/validate_evidence",
        json={
            "query": "Unknown topic",
            "synthesized_answer": "I do not have verified knowledge.",
            "candidates": [],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False
    assert body["retrieval_run_record"]["verification_status"] == "NO_VERIFIED_KNOWLEDGE"


def test_api_authority_map_returns_all_tiers(client):
    resp = client.get("/v2/convergence/authority_map")
    assert resp.status_code == 200
    data = resp.json()
    tiers = {v["authority_tier"] for v in data.values()}
    assert "CANONICAL" in tiers
    assert "DERIVED" in tiers
    assert "FALLBACK" in tiers
    assert "TEST_FIXTURE" in tiers


def test_api_authority_map_masterdb_is_canonical(client):
    resp = client.get("/v2/convergence/authority_map")
    assert resp.status_code == 200
    data = resp.json()
    assert data["MASTERDB"]["authority_tier"] == "CANONICAL"
    assert data["MASTERDB"]["is_queried"] is True
    assert data["MASTERDB"]["has_provenance"] is True


def test_api_authority_map_llm_fallback_is_not_queried(client):
    resp = client.get("/v2/convergence/authority_map")
    assert resp.status_code == 200
    data = resp.json()
    assert data["LLM_FALLBACK"]["authority_tier"] == "FALLBACK"
    assert data["LLM_FALLBACK"]["is_queried"] is False


# ---------------------------------------------------------------------------
# 4. API Contract Boundaries — auth and field contracts
# ---------------------------------------------------------------------------

def test_authority_map_endpoint_requires_no_auth(client):
    resp = client.get("/v2/convergence/authority_map")
    assert resp.status_code == 200


def test_validate_evidence_trace_fields_are_present(client):
    resp = client.post(
        "/v2/convergence/validate_evidence",
        json={
            "query": "What is karma?",
            "synthesized_answer": "Karma is the causal continuity of action.",
            "candidates": [
                {"content": "Karma is the causal continuity of action.", "source": "MASTERDB", "concept": "karma"}
            ],
        },
    )
    assert resp.status_code == 200
    record = resp.json()["retrieval_run_record"]
    for field in ("query_id", "trace_id", "replay_id", "retrieval_run_id", "index_version"):
        assert field in record, f"Missing contract field: {field}"


def test_validate_evidence_selected_evidence_has_provenance_hashes(client):
    resp = client.post(
        "/v2/convergence/validate_evidence",
        json={
            "query": "What is dharma?",
            "synthesized_answer": "Dharma is the sustaining order of life and duty.",
            "candidates": [
                {"content": "Dharma is the sustaining order of life and duty.", "source": "MASTERDB", "concept": "dharma"}
            ],
        },
    )
    assert resp.status_code == 200
    evidence = resp.json()["retrieval_run_record"]["selected_evidence"]
    assert len(evidence) > 0
    for item in evidence:
        assert item["provenance_hash"], "provenance_hash must not be empty"
        assert item["canonical_object_id"].startswith("uko:")


def test_validate_evidence_claim_bindings_have_verification_status(client):
    resp = client.post(
        "/v2/convergence/validate_evidence",
        json={
            "query": "What is dharma?",
            "synthesized_answer": "Dharma is the sustaining order of life and duty.",
            "candidates": [
                {"content": "Dharma is the sustaining order of life and duty.", "source": "MASTERDB", "concept": "dharma"}
            ],
        },
    )
    assert resp.status_code == 200
    bindings = resp.json()["retrieval_run_record"]["claim_bindings"]
    assert len(bindings) > 0
    for b in bindings:
        assert b["verification_status"] in ("VERIFIED", "DERIVED", "UNVERIFIED_FALLBACK", "CONTRADICTED")


# ---------------------------------------------------------------------------
# 5. Deterministic Execution — replay ID and provenance hash stability
# ---------------------------------------------------------------------------

def test_replay_id_is_stable_for_identical_inputs(runtime):
    candidates = [{"content": "Atman is the inner conscious self.", "source": "AKASHIC", "concept": "atman"}]
    r1, _ = runtime.process_query_run(
        query="What is Atman?",
        candidates=candidates,
        synthesized_answer="Atman is the inner conscious self.",
        trace_id="determinism_trace_001",
    )
    r2, _ = runtime.process_query_run(
        query="What is Atman?",
        candidates=candidates,
        synthesized_answer="Atman is the inner conscious self.",
        trace_id="determinism_trace_001",
    )
    assert r1.replay_id == r2.replay_id


def test_provenance_hash_is_stable_for_identical_canonical_objects():
    from convergence.canonical_object import create_canonical_object
    obj1 = create_canonical_object(concept_id="dharma", source_id="MASTERDB", text_span="Dharma is duty.")
    obj2 = create_canonical_object(concept_id="dharma", source_id="MASTERDB", text_span="Dharma is duty.")
    assert obj1.provenance_hash == obj2.provenance_hash
    assert obj1.canonical_object_id == obj2.canonical_object_id


def test_provenance_hash_changes_when_text_span_changes():
    from convergence.canonical_object import create_canonical_object
    obj1 = create_canonical_object(concept_id="dharma", source_id="MASTERDB", text_span="Dharma is duty.")
    obj2 = create_canonical_object(concept_id="dharma", source_id="MASTERDB", text_span="Dharma is cosmic order.")
    assert obj1.provenance_hash != obj2.provenance_hash
    assert obj1.canonical_object_id != obj2.canonical_object_id


def test_selected_evidence_hashes_are_stable_across_runs(runtime):
    candidates = [{"content": "Karma is the causal continuity of action.", "source": "MASTERDB", "concept": "karma"}]
    r1, _ = runtime.process_query_run(
        query="What is karma?",
        candidates=candidates,
        synthesized_answer="Karma is the causal continuity of action.",
        trace_id="hash_stable_trace",
    )
    r2, _ = runtime.process_query_run(
        query="What is karma?",
        candidates=candidates,
        synthesized_answer="Karma is the causal continuity of action.",
        trace_id="hash_stable_trace",
    )
    assert r1.selected_evidence[0].provenance_hash == r2.selected_evidence[0].provenance_hash
    assert r1.claim_bindings[0].provenance_hash == r2.claim_bindings[0].provenance_hash


def test_replay_safe_is_always_true(runtime):
    record, _ = runtime.process_query_run(
        query="What is dharma?",
        candidates=_canonical_candidates(),
        synthesized_answer="Dharma is the sustaining order of life and duty.",
    )
    assert record.replay_safe is True


# ---------------------------------------------------------------------------
# 6. Trust Validation — authority tier enforcement and claim binding
# ---------------------------------------------------------------------------

def test_canonical_source_produces_verified_claim_binding(runtime):
    from convergence.retrieval_evidence_contract import ClaimVerificationStatus
    record, _ = runtime.process_query_run(
        query="What is dharma?",
        candidates=[{"content": "Dharma is the sustaining order of life and duty.", "source": "MASTERDB", "concept": "dharma"}],
        synthesized_answer="Dharma is the sustaining order of life and duty.",
    )
    assert record.claim_bindings[0].verification_status == ClaimVerificationStatus.VERIFIED


def test_derived_source_produces_derived_claim_binding(runtime):
    from convergence.retrieval_evidence_contract import ClaimVerificationStatus
    record, _ = runtime.process_query_run(
        query="What is dharma?",
        candidates=[{"content": "Dharma is the sustaining order of life and duty.", "source": "FAISS_VECTOR_INDEX", "concept": "dharma"}],
        synthesized_answer="Dharma is the sustaining order of life and duty.",
    )
    assert record.claim_bindings[0].verification_status == ClaimVerificationStatus.DERIVED


def test_fallback_source_produces_unverified_fallback_binding(runtime):
    from convergence.retrieval_evidence_contract import ClaimVerificationStatus
    record, _ = runtime.process_query_run(
        query="Speculative topic",
        candidates=_fallback_candidates(),
        synthesized_answer="Unverified LLM draft text.",
    )
    assert record.claim_bindings[0].verification_status == ClaimVerificationStatus.UNVERIFIED_FALLBACK


def test_test_fixture_source_is_classified_correctly():
    from convergence.authority_contract import get_authority_map, AuthorityTier
    amap = get_authority_map()
    src = amap.get_source("TEST_FIXTURE")
    assert src is not None
    assert src.authority_tier == AuthorityTier.TEST_FIXTURE
    assert src.influences_answers is False


def test_canonical_object_schema_version_is_correct():
    from convergence.canonical_object import create_canonical_object, SCHEMA_VERSION
    obj = create_canonical_object(concept_id="karma", source_id="MASTERDB", text_span="Karma is action.")
    assert obj.schema_version == SCHEMA_VERSION
    assert obj.schema_version == "UNIGURU_CANONICAL_OBJECT_V1"


def test_canonical_object_id_uses_uko_prefix():
    from convergence.canonical_object import create_canonical_object
    obj = create_canonical_object(concept_id="Dharma", source_id="MASTERDB", text_span="Dharma is duty.")
    assert obj.canonical_object_id.startswith("uko:")
