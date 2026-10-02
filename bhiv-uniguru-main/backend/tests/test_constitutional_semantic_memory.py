from __future__ import annotations

import json
from pathlib import Path

from memory.constitutional_semantic_memory import ConstitutionalSemanticMemory, stable_hash
from ontology.drift_detector import detect_semantic_drift


def _store(tmp_path: Path) -> ConstitutionalSemanticMemory:
    return ConstitutionalSemanticMemory(
        event_log_path=tmp_path / "events.jsonl",
        checkpoint_path=tmp_path / "checkpoint.json",
        observability_path=tmp_path / "observability.json",
    )


def _accepted_request(**overrides):
    request = {
        "trace_id": "test_trace",
        "user_id": "tester",
        "query": "What is governed semantic memory?",
        "accepted_signals": [
            {
                "signal_id": "signal_1",
                "source": "test_source",
                "domain": "core",
                "_validation": {
                    "candidate_entities": [{"canonical": "Governed Semantic Memory"}],
                },
            }
        ],
        "rejected_signals": [],
        "consensus": {"contradictions": [], "contradiction_pressure": 0.0},
        "verification_status": "VERIFIED",
        "retrieval_truth_hash": stable_hash({"retrieval": "truth"}),
        "interpretation_hash": stable_hash({"interpretation": "bounded"}),
        "authority_boundary": {
            "boundary_status": "ENFORCED",
            "interpretation_references_retrieval": True,
        },
        "confidence": 0.8,
        "ontology_lineage": [{"concept_id": "core"}],
    }
    request.update(overrides)
    return request


def test_canonical_mutation_is_idempotent_and_reconstructable(tmp_path):
    store = _store(tmp_path)
    first = store.record_pipeline_mutation(_accepted_request())
    replay = store.record_pipeline_mutation(_accepted_request())
    reconstruction = store.reconstruct()

    assert first["event_hash"] == replay["event_hash"]
    assert replay["idempotent_replay"] is True
    assert first["governance_decision"]["memory_classification"] == "canonical"
    assert "Governed Semantic Memory" in reconstruction["canonical_memory"]
    assert reconstruction["replay_integrity"]["hash_chain_ok"] is True


def test_contradiction_is_quarantined_not_canonical(tmp_path):
    store = _store(tmp_path)
    result = store.record_pipeline_mutation(
        _accepted_request(
            trace_id="contradiction_trace",
            consensus={
                "contradictions": [{"claim_key": "Governed Semantic Memory"}],
                "contradiction_pressure": 1.0,
            },
        )
    )
    reconstruction = store.reconstruct()

    assert result["governance_decision"]["memory_classification"] == "quarantined"
    assert result["canonical_authority_granted"] is False
    assert reconstruction["canonical_memory"] == {}
    assert reconstruction["contradiction_audit"]


def test_poisoning_attempt_without_retrieval_truth_stays_transient(tmp_path):
    store = _store(tmp_path)
    result = store.record_pipeline_mutation(
        _accepted_request(
            trace_id="poison_trace",
            retrieval_truth_hash=None,
            authority_boundary={
                "boundary_status": "BYPASSED",
                "interpretation_references_retrieval": False,
            },
            confidence=0.99,
        )
    )

    assert result["governance_decision"]["decision"] == "REJECT_CANONICAL_MUTATION"
    assert "missing_retrieval_truth_hash" in result["governance_decision"]["reasons"]
    assert "truth_interpretation_boundary_not_enforced" in result["governance_decision"]["reasons"]


def test_rollback_and_corruption_detection(tmp_path):
    store = _store(tmp_path)
    first = store.record_pipeline_mutation(_accepted_request(trace_id="trace_1"))
    store.record_pipeline_mutation(_accepted_request(trace_id="trace_2", query="Second query"))

    rollback = store.rollback_preview(first["event_hash"])
    assert rollback["event_count"] == 1
    assert rollback["replay_integrity"]["hash_chain_ok"] is True

    events = store.read_events()
    events[-1]["trace_id"] = "tampered"
    corrupt_path = tmp_path / "corrupt.jsonl"
    corrupt_path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=True, sort_keys=True) for event in events) + "\n",
        encoding="utf-8",
    )
    corrupt_store = ConstitutionalSemanticMemory(event_log_path=corrupt_path)
    assert corrupt_store.reconstruct()["replay_integrity"]["hash_chain_ok"] is False


def test_ontology_mutation_requires_lineage_safe_versioning():
    previous = {
        "snapshot_version": 1,
        "concepts": [
            {
                "concept_id": "1",
                "canonical_name": "Root",
                "parent_id": None,
                "truth_level": 3,
                "domain": "core",
                "immutable": False,
            }
        ],
    }
    current = {
        "snapshot_version": 1,
        "concepts": [
            {
                "concept_id": "1",
                "canonical_name": "Root Renamed",
                "parent_id": None,
                "truth_level": 3,
                "domain": "core",
                "immutable": False,
            }
        ],
    }

    drift = detect_semantic_drift(previous, current)
    assert drift["accepted"] is False
    assert drift["violations"][0]["type"] == "canonical_name_change_requires_version_bump"
