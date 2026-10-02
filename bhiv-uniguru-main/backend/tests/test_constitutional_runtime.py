from __future__ import annotations

from governance.constitutional_runtime import ConstitutionalCognitionRuntime


def _fixture():
    previous = {
        "snapshot_version": 1,
        "concepts": [
            {
                "concept_id": "root",
                "canonical_name": "Governed Claim",
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
                "concept_id": "root",
                "canonical_name": "Self-Legitimized Claim",
                "parent_id": None,
                "truth_level": 3,
                "domain": "core",
                "immutable": False,
            }
        ],
    }
    events = [
        {
            "trace_id": "runtime_1",
            "claim_key": "governed_claim",
            "confidence": 0.41,
            "provenance_weight": 0.31,
            "legitimacy_evidence": 0.22,
            "reinforcement_count": 1,
            "contradiction_pressure": 0.0,
            "uncertainty": 0.45,
            "ambiguity_class": "weak_provenance",
            "unresolved": True,
        },
        {
            "trace_id": "runtime_2",
            "claim_key": "governed_claim",
            "confidence": 0.93,
            "provenance_weight": 0.34,
            "legitimacy_evidence": 0.27,
            "reinforcement_count": 6,
            "contradiction_pressure": 0.76,
            "uncertainty": 0.52,
            "ambiguity_class": "conflicting_claims",
            "unresolved": True,
        },
    ]
    return {
        "previous_snapshot": previous,
        "current_snapshot": current,
        "semantic_events": events,
        "ontology_boundaries": {"governed_claim": {"legitimacy_ceiling": 0.35, "ontology_violation_count": 1}},
        "disputes": [
            {
                "claim_key": "governed_claim",
                "signal_ids": ["semantic_node", "replay_node"],
                "polarities": ["bounded", "authoritative"],
                "contradiction_pressure": 0.76,
            }
        ],
        "arbitrators": [{"node_id": "vijay"}, {"node_id": "yashika"}, {"node_id": "tester"}],
        "prior_unresolved": {"governed_claim": 1},
        "claims": [
            {
                "claim_key": "governed_claim",
                "concept_id": "root",
                "requested_legitimacy": 0.87,
                "uncertainty": 0.52,
                "contradiction_pressure": 0.76,
            }
        ],
    }


def test_constitutional_runtime_replay_is_deterministic():
    first = ConstitutionalCognitionRuntime.execute(**_fixture())
    replay = ConstitutionalCognitionRuntime.execute(**_fixture())

    assert first["runtime_trace"]["runtime_hash"] == replay["runtime_trace"]["runtime_hash"]
    assert first["replay_flow"]["replay_safe"] is True
    assert first["runtime_trace"]["canonical_authority_granted"] is False
    assert first["runtime_trace"]["event_registry_verification"]["hash_chain_ok"] is True


def test_runtime_reconstruction_and_rollback_are_hash_safe():
    result = ConstitutionalCognitionRuntime.execute(**_fixture())
    reconstruction = ConstitutionalCognitionRuntime.reconstruct(result["runtime_trace"])
    lineage = result["lineage_proof"]

    assert reconstruction["hash_chain_ok"] is True
    assert reconstruction["event_count"] == 7
    assert lineage["rollback_authenticity"]["rollback_hash_chain_ok"] is True
    assert lineage["lineage_disciplines"]["observability"] == "non_authoritative"


def test_runtime_rejects_forged_replay_and_detects_corruption():
    result = ConstitutionalCognitionRuntime.execute(**_fixture())
    failures = ConstitutionalCognitionRuntime.simulate_failures(result["runtime_trace"])

    assert failures["forged_replay"]["rejected"] is True
    assert failures["semantic_corruption"]["detected"] is True
    assert failures["contradiction_continuity_preserved"] is True
    assert failures["ontology_lineage_continuity_preserved"] is True


def test_runtime_converges_governance_trust_contradiction_and_observability():
    result = ConstitutionalCognitionRuntime.execute(**_fixture())
    components = result["components"]

    assert components["semantic_governance"]["canonical_authority_granted"] is False
    assert components["trust_propagation"]["authority_pressure_logs"][0]["governance_response"] == "ESCALATE_SEMANTIC_PRESSURE"
    assert components["contradiction_escalation"]["unresolved_contradiction_persistence"]
    assert components["ontology_lineage"]["semantic_drift_alerts"]
    assert components["observability"]["replay_safe"] is True
