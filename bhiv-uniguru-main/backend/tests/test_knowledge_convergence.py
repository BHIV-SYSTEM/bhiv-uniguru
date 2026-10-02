"""
Comprehensive Validation Suite for UniGuru Knowledge Convergence & Trust Validation Layer.
Owner: Isha Singh

Covers all 11 required validation scenarios:
1. Overlapping chunks deduplication
2. Duplicate corpus entries
3. Same term, different meaning (homonyms)
4. Same concept, different Darśana/tradition
5. Conflicting commentaries
6. Sanskrit vs English query variation
7. Narrow vs broad queries
8. Missing canonical evidence
9. Fallback invocation visibility
10. Index rebuild validation
11. Deterministic / replayable retrieval evidence
"""

import pytest
from fastapi.testclient import TestClient
from convergence.authority_contract import AuthorityTier, get_authority_map
from convergence.canonical_object import create_canonical_object, CanonicalKnowledgeObject
from convergence.retrieval_evidence_contract import (
    RetrievedEvidenceItem,
    ClaimEvidenceBinding,
    ClaimVerificationStatus,
    RetrievalRunRecord,
)
from convergence.convergence_runtime import KnowledgeConvergenceRuntime, run_convergence_pipeline
from service.uniguru_runtime_api import app


@pytest.fixture
def runtime() -> KnowledgeConvergenceRuntime:
    return KnowledgeConvergenceRuntime()


def test_1_overlapping_chunks_deduplication(runtime: KnowledgeConvergenceRuntime):
    candidates = [
        {"content": "Dharma is the sustaining order of life and duty.", "source": "MASTERDB", "concept": "dharma"},
        {"content": "Dharma is the sustaining order of life and duty.", "source": "AKASHIC", "concept": "dharma"}, # Duplicate
        {"content": "Dharma governs cosmic and moral conduct.", "source": "KOSHA", "concept": "dharma"},
    ]
    record, deduped = runtime.process_query_run(
        query="What is dharma?",
        candidates=candidates,
        synthesized_answer="Dharma is the sustaining order of life and duty.",
    )
    assert record.candidate_count == 3
    assert record.deduplicated_candidate_count == 2
    assert len(deduped) == 2
    assert record.selected_evidence[0].dedup_status == "unique"


def test_2_duplicate_corpus_entries(runtime: KnowledgeConvergenceRuntime):
    candidates = [
        {"content": "Karma is the causal continuity of action.", "source": "MASTERDB", "concept": "karma"},
        {"content": "Karma is the causal continuity of action.", "source": "FAISS_VECTOR_INDEX", "concept": "karma"},
    ]
    record, _ = runtime.process_query_run(
        query="Explain karma",
        candidates=candidates,
        synthesized_answer="Karma is the causal continuity of action.",
    )
    assert record.candidate_count == 2
    assert record.deduplicated_candidate_count == 1


def test_3_same_term_different_meaning_homonyms(runtime: KnowledgeConvergenceRuntime):
    candidates = [
        {"content": "Kala as time orders the cyclic unfolding of worlds.", "source": "AKASHIC", "concept": "kala_time", "tradition": "cosmology"},
        {"content": "Kala as black or dark color signifies unmanifest potentiality.", "source": "AKASHIC", "concept": "kala_color", "tradition": "symbolism"},
    ]
    record, _ = runtime.process_query_run(
        query="What is Kala in Indian philosophy?",
        candidates=candidates,
        synthesized_answer="Kala as time orders the cyclic unfolding of worlds. Kala as dark color signifies unmanifest potentiality.",
    )
    assert len(record.selected_evidence) == 2
    assert record.selected_evidence[0].tradition_context == "cosmology"
    assert record.selected_evidence[1].tradition_context == "symbolism"


def test_4_same_concept_different_darsana_traditions(runtime: KnowledgeConvergenceRuntime):
    candidates = [
        {"content": "Advaita interprets dharma as the expression of the ordered self.", "source": "AKASHIC", "concept": "dharma", "tradition": "advaita"},
        {"content": "Dvaita interprets dharma as the law of distinctions and divine order.", "source": "AKASHIC", "concept": "dharma", "tradition": "dvaita"},
    ]
    record, _ = runtime.process_query_run(
        query="Compare Advaita and Dvaita on Dharma",
        candidates=candidates,
        synthesized_answer="Advaita interprets dharma as the expression of the ordered self. Dvaita interprets dharma as divine order.",
    )
    assert len(record.selected_evidence) == 2
    traditions = {e.tradition_context for e in record.selected_evidence}
    assert "advaita" in traditions
    assert "dvaita" in traditions


def test_5_conflicting_commentaries(runtime: KnowledgeConvergenceRuntime):
    candidates = [
        {"content": "Commentary A asserts action is primary in ritual.", "source": "AKASHIC", "concept": "yajna", "tradition": "mimamsa"},
        {"content": "Commentary B asserts knowledge is primary over ritual action.", "source": "AKASHIC", "concept": "yajna", "tradition": "vedanta"},
    ]
    record, _ = runtime.process_query_run(
        query="Is yajna action or knowledge?",
        candidates=candidates,
        synthesized_answer="Mimamsa asserts action is primary in ritual while Vedanta asserts knowledge is primary.",
    )
    assert record.verification_status in ["VERIFIED", "PARTIAL_VERIFIED"]
    assert len(record.claim_bindings) >= 1


def test_6_sanskrit_vs_english_query_variation(runtime: KnowledgeConvergenceRuntime):
    cand_sanskrit = [
        {"content": "प्राणः जीवनशक्तिः अस्ति।", "source": "AKASHIC", "concept": "prana"},
    ]
    cand_english = [
        {"content": "Prana is the vital force governing life.", "source": "MASTERDB", "concept": "prana"},
    ]
    res_sanskrit, _ = runtime.process_query_run(query="प्राणः कः?", candidates=cand_sanskrit, synthesized_answer="प्राणः जीवनशक्तिः अस्ति।")
    res_english, _ = runtime.process_query_run(query="What is Prana?", candidates=cand_english, synthesized_answer="Prana is the vital force governing life.")
    assert res_sanskrit.verification_status == "VERIFIED"
    assert res_english.verification_status == "VERIFIED"


def test_7_narrow_vs_broad_queries(runtime: KnowledgeConvergenceRuntime):
    candidates = [
        {"content": "Prana is vital breath. Annamaya is food sheath. Chakras are energy centers.", "source": "AKASHIC", "concept": "subtle_body"},
    ]
    narrow_res, _ = runtime.process_query_run(query="What is Annamaya Kosha?", candidates=candidates, synthesized_answer="Annamaya is food sheath.", semantic_scope="narrow")
    broad_res, _ = runtime.process_query_run(query="Explain the human psycho-spiritual anatomy", candidates=candidates, synthesized_answer="Prana is vital breath. Annamaya is food sheath. Chakras are energy centers.", semantic_scope="broad")
    assert narrow_res.semantic_scope == "narrow"
    assert broad_res.semantic_scope == "broad"


def test_8_missing_canonical_evidence(runtime: KnowledgeConvergenceRuntime):
    candidates = []
    record, _ = runtime.process_query_run(
        query="What is the stock price of Apple?",
        candidates=candidates,
        synthesized_answer="I do not have verified knowledge to answer this question.",
    )
    assert record.candidate_count == 0
    assert record.verification_status == "NO_VERIFIED_KNOWLEDGE"
    assert record.claim_bindings[0].verification_status == ClaimVerificationStatus.UNVERIFIED_FALLBACK


def test_9_fallback_invocation_visibility(runtime: KnowledgeConvergenceRuntime):
    candidates = [
        {"content": "Unverified LLM draft text.", "source": "LLM_FALLBACK", "concept": "unverified", "authority_tier": "FALLBACK"},
    ]
    record, _ = runtime.process_query_run(
        query="Speculative theory",
        candidates=candidates,
        synthesized_answer="Unverified LLM draft text.",
    )
    assert record.selected_evidence[0].authority_tier == AuthorityTier.FALLBACK
    assert record.claim_bindings[0].verification_status == ClaimVerificationStatus.UNVERIFIED_FALLBACK


def test_10_index_rebuild_validation():
    obj1 = create_canonical_object(concept_id="dharma", source_id="MASTERDB", text_span="Dharma is duty.")
    obj2 = create_canonical_object(concept_id="dharma", source_id="MASTERDB", text_span="Dharma is duty.") # Rebuilt
    assert obj1.canonical_object_id == obj2.canonical_object_id
    assert obj1.provenance_hash == obj2.provenance_hash
    assert obj1.authority_tier == AuthorityTier.CANONICAL


def test_11_deterministic_replayable_retrieval_evidence(runtime: KnowledgeConvergenceRuntime):
    candidates = [
        {"content": "Atman is the inner conscious self.", "source": "AKASHIC", "concept": "atman"},
    ]
    record1, _ = runtime.process_query_run(query="What is Atman?", candidates=candidates, synthesized_answer="Atman is the inner conscious self.", trace_id="trace_stable_123")
    record2, _ = runtime.process_query_run(query="What is Atman?", candidates=candidates, synthesized_answer="Atman is the inner conscious self.", trace_id="trace_stable_123")
    assert record1.replay_id == record2.replay_id
    assert record1.selected_evidence[0].provenance_hash == record2.selected_evidence[0].provenance_hash
    assert record1.replay_safe is True


def test_12_api_convergence_endpoints():
    client = TestClient(app)
    resp_map = client.get("/v2/convergence/authority_map")
    assert resp_map.status_code == 200
    data_map = resp_map.json()
    assert "MASTERDB" in data_map
    assert data_map["FAISS_VECTOR_INDEX"]["authority_tier"] == "DERIVED"

    resp_val = client.post(
        "/v2/convergence/validate_evidence",
        json={
            "query": "What is Dharma?",
            "synthesized_answer": "Dharma is the sustaining order of life and duty.",
            "candidates": [{"content": "Dharma is the sustaining order of life and duty.", "source": "MASTERDB", "concept": "dharma"}],
        },
    )
    assert resp_val.status_code == 200
    val_data = resp_val.json()
    assert val_data["valid"] is True
    assert val_data["retrieval_run_record"]["deduplicated_candidate_count"] == 1
