from __future__ import annotations

from governance.semantic_authority import (
    AuthorityPressureGovernanceEngine,
    ContradictionEscalationGovernance,
    DistributedContradictionArbitrator,
    OntologyLegitimacyBoundaryEngine,
    SemanticDriftObservabilityEngine,
    SemanticPressureObservabilityEngine,
    TrustBoundSemanticWeightingFramework,
    UncertaintyLineageTracker,
)


def _snapshots():
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
    return previous, current


def _events():
    return [
        {
            "trace_id": "semantic_pressure_1",
            "claim_key": "governed_claim",
            "confidence": 0.41,
            "reinforcement_count": 1,
            "contradiction_pressure": 0.0,
            "uncertainty": 0.48,
            "ambiguity_class": "interpretive",
            "unresolved": True,
        },
        {
            "trace_id": "semantic_pressure_2",
            "claim_key": "governed_claim",
            "confidence": 0.92,
            "reinforcement_count": 5,
            "contradiction_pressure": 0.75,
            "uncertainty": 0.52,
            "ambiguity_class": "conflicting_claims",
            "unresolved": True,
        },
    ]


def test_semantic_drift_observability_exposes_pressure_without_authority():
    previous, current = _snapshots()
    telemetry = SemanticDriftObservabilityEngine.observe(
        previous_snapshot=previous,
        current_snapshot=current,
        semantic_events=_events(),
    )

    assert telemetry["observable_only"] is True
    assert telemetry["canonical_authority_granted"] is False
    assert telemetry["ontology_drift"]["accepted"] is False
    assert telemetry["ontology_drift"]["violations"][0]["type"] == "canonical_name_change_requires_version_bump"
    assert telemetry["confidence_pressure"]["inflation_detected"] is True
    assert telemetry["reinforcement_pressure"]["authority_accumulation_detected"] is True
    assert telemetry["semantic_continuity_pressure"]["bounded_continuity_required"] is True
    assert telemetry["authority_gravity"]["authority_gravity_detected"] is True
    assert telemetry["telemetry_hash"]


def test_contradiction_escalation_preserves_lineage_and_blocks_silent_merge():
    result = ContradictionEscalationGovernance.evaluate(
        contradictions=[
            {
                "claim_key": "governed_claim",
                "signal_ids": ["signal_a", "signal_b"],
                "polarities": ["affirmative", "negative"],
            }
        ],
        signals=[{"signal_id": "signal_a"}, {"signal_id": "signal_b"}],
        prior_unresolved_count=0,
        quorum_required=2,
    )

    assert result["lifecycle_state"] == "ESCALATED"
    assert result["action"] == "QUARANTINE_AND_REQUIRE_REVIEW"
    assert result["canonical_authority_granted"] is False
    assert result["lineage_preserved"] is True
    assert result["silent_merge_allowed"] is False
    assert result["audit_hash"]


def test_persistent_unresolved_contradiction_escalates_harder():
    result = ContradictionEscalationGovernance.evaluate(
        contradictions=[{"claim_key": "governed_claim"}],
        signals=[{"signal_id": "signal_a"}],
        prior_unresolved_count=2,
    )

    assert result["lifecycle_state"] == "PERSISTENT_UNRESOLVED"
    assert result["action"] == "QUARANTINE_AND_ESCALATE_REVIEW"


def test_weighting_rejects_confidence_inflation_as_legitimacy():
    result = TrustBoundSemanticWeightingFramework.score(
        confidence=0.94,
        prior_confidence=0.42,
        provenance_weight=0.36,
        legitimacy_evidence=0.22,
        reinforcement_count=6,
        contradiction_pressure=0.2,
        uncertainty=0.44,
    )

    assert result["confidence_inflation_detected"] is True
    assert result["reinforcement_abuse_detected"] is True
    assert result["boundary_decision"] == "REJECT_LEGITIMACY_ESCALATION"
    assert result["trust_score"] < result["confidence"]
    assert result["discipline"]["confidence_is_not_legitimacy"] is True
    assert result["discipline"]["reinforcement_is_not_truth_authority"] is True


def test_uncertainty_lineage_reconstruction_is_replay_safe():
    first = UncertaintyLineageTracker.reconstruct(_events(), lineage_id="lineage_fixture")
    replay = UncertaintyLineageTracker.reconstruct(_events(), lineage_id="lineage_fixture")

    assert first["replay_safe"] is True
    assert first["lineage_state_hash"] == replay["lineage_state_hash"]
    assert first["lineage"][1]["previous_lineage_hash"] == first["lineage"][0]["lineage_hash"]
    assert first["lineage"][1]["contradiction_pressure"] == 0.75


def test_authority_pressure_forecast_rejects_legitimacy_accumulation():
    pressure = AuthorityPressureGovernanceEngine.evaluate(
        semantic_events=[
            {
                "trace_id": "pressure_1",
                "claim_key": "governed_claim",
                "confidence": 0.4,
                "provenance_weight": 0.32,
                "legitimacy_evidence": 0.24,
                "reinforcement_count": 1,
                "contradiction_pressure": 0.0,
                "uncertainty": 0.44,
                "unresolved": True,
            },
            {
                "trace_id": "pressure_2",
                "claim_key": "governed_claim",
                "confidence": 0.93,
                "provenance_weight": 0.34,
                "legitimacy_evidence": 0.28,
                "reinforcement_count": 6,
                "contradiction_pressure": 0.8,
                "uncertainty": 0.53,
                "unresolved": True,
            },
        ],
        ontology_boundaries={"governed_claim": {"legitimacy_ceiling": 0.35, "ontology_violation_count": 1}},
    )

    row = pressure["authority_pressure_logs"][0]
    forecast = pressure["semantic_legitimacy_forecast"][0]
    decay = pressure["trust_decay_simulation"][0]
    assert row["canonical_authority_granted"] is False
    assert row["governance_response"] == "ESCALATE_SEMANTIC_PRESSURE"
    assert forecast["escalation_required"] is True
    assert forecast["confidence_not_legitimacy"] is True
    assert decay["final_trust"] <= decay["initial_trust"]
    assert pressure["governance_hash"]


def test_distributed_contradiction_arbitration_preserves_unresolved_lineage():
    arbitration = DistributedContradictionArbitrator.arbitrate(
        disputes=[
            {
                "claim_key": "governed_claim",
                "signal_ids": ["node_a", "node_b", "node_c"],
                "polarities": ["affirmative", "negative"],
                "contradiction_pressure": 0.82,
            }
        ],
        arbitrators=[{"node_id": "vijay"}, {"node_id": "tester"}, {"node_id": "akash"}],
        prior_unresolved={"governed_claim": 2},
    )

    row = arbitration["contradiction_arbitration_trace"][0]
    assert row["lifecycle_state"] == "PERSISTENT_UNRESOLVED"
    assert row["canonical_authority_granted"] is False
    assert arbitration["silent_merge_allowed"] is False
    assert arbitration["unresolved_contradiction_persistence"][0]["persistence_state"] == "open"
    assert arbitration["arbitration_hash"]


def test_ontology_legitimacy_caps_emit_drift_alerts():
    previous, current = _snapshots()
    result = OntologyLegitimacyBoundaryEngine.evaluate(
        previous_snapshot=previous,
        current_snapshot=current,
        claims=[
            {
                "claim_key": "governed_claim",
                "concept_id": "root",
                "requested_legitimacy": 0.9,
                "uncertainty": 0.5,
                "contradiction_pressure": 0.7,
            }
        ],
    )

    boundary = result["ontology_legitimacy_boundaries"][0]
    assert boundary["semantic_legitimacy_cap"] <= boundary["ontology_legitimacy_ceiling"]
    assert boundary["canonical_authority_granted"] is False
    assert result["semantic_drift_alerts"]
    assert result["ontology_pressure_observability"]["mutation_pressure_score"] > 0


def test_semantic_pressure_observability_replay_is_stable():
    pressure = AuthorityPressureGovernanceEngine.evaluate(
        semantic_events=_events(),
        ontology_boundaries={"governed_claim": {"legitimacy_ceiling": 0.36, "ontology_violation_count": 1}},
    )
    arbitration = DistributedContradictionArbitrator.arbitrate(
        disputes=[
            {
                "claim_key": "governed_claim",
                "signal_ids": ["signal_a", "signal_b"],
                "polarities": ["affirmative", "negative"],
                "contradiction_pressure": 0.75,
            }
        ],
        arbitrators=[{"node_id": "vijay"}, {"node_id": "tester"}],
        prior_unresolved={"governed_claim": 1},
    )
    ontology = OntologyLegitimacyBoundaryEngine.evaluate(
        previous_snapshot=_snapshots()[0],
        current_snapshot=_snapshots()[1],
        claims=[
            {
                "claim_key": "governed_claim",
                "concept_id": "root",
                "requested_legitimacy": 0.85,
                "uncertainty": 0.52,
                "contradiction_pressure": 0.75,
            }
        ],
    )
    uncertainty = UncertaintyLineageTracker.reconstruct(_events(), lineage_id="pressure_observability")
    first = SemanticPressureObservabilityEngine.build(
        pressure_governance=pressure,
        contradiction_arbitration=arbitration,
        ontology_boundaries=ontology,
        uncertainty_lineage=uncertainty,
    )
    replay = SemanticPressureObservabilityEngine.build(
        pressure_governance=pressure,
        contradiction_arbitration=arbitration,
        ontology_boundaries=ontology,
        uncertainty_lineage=uncertainty,
    )

    assert first["replay_safe"] is True
    assert first["observability_hash"] == replay["observability_hash"]
    assert first["semantic_pressure_observability"]["governance_state"] == "ESCALATED"
    assert first["authority_gravity_dashboard"]["dashboard_mode"] == "json_only"
