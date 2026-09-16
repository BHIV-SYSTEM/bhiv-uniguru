from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PROOF_DIR = ROOT / "review_packets" / "proof_logs"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from governance.semantic_authority import (
    AuthorityPressureGovernanceEngine,
    DistributedContradictionArbitrator,
    OntologyLegitimacyBoundaryEngine,
    SemanticPressureObservabilityEngine,
    UncertaintyLineageTracker,
)
from memory.constitutional_semantic_memory import stable_hash


def write(name: str, payload: Dict[str, Any]) -> None:
    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    (PROOF_DIR / name).write_text(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")


def previous_snapshot() -> Dict[str, Any]:
    return {
        "snapshot_version": 2,
        "concepts": [
            {
                "concept_id": "governed_claim",
                "canonical_name": "Governed Semantic Claim",
                "parent_id": None,
                "truth_level": 3,
                "domain": "core",
                "immutable": False,
            },
            {
                "concept_id": "civilizational_memory",
                "canonical_name": "Civilizational Memory",
                "parent_id": "governed_claim",
                "truth_level": 4,
                "domain": "tantra",
                "immutable": True,
            },
        ],
    }


def current_snapshot() -> Dict[str, Any]:
    return {
        "snapshot_version": 2,
        "concepts": [
            {
                "concept_id": "governed_claim",
                "canonical_name": "Self-Legitimized Semantic Claim",
                "parent_id": None,
                "truth_level": 3,
                "domain": "core",
                "immutable": False,
            },
            {
                "concept_id": "civilizational_memory",
                "canonical_name": "Civilizational Memory Authority",
                "parent_id": "governed_claim",
                "truth_level": 3,
                "domain": "tantra",
                "immutable": True,
            },
        ],
    }


def semantic_events() -> list[Dict[str, Any]]:
    return [
        {
            "trace_id": "pressure_trace_001",
            "claim_key": "governed_claim",
            "confidence": 0.42,
            "provenance_weight": 0.31,
            "legitimacy_evidence": 0.24,
            "reinforcement_count": 1,
            "contradiction_pressure": 0.0,
            "uncertainty": 0.44,
            "ambiguity_class": "interpretive_or_weak_evidence_zone",
            "unresolved": True,
        },
        {
            "trace_id": "pressure_trace_002",
            "claim_key": "governed_claim",
            "confidence": 0.91,
            "provenance_weight": 0.34,
            "legitimacy_evidence": 0.28,
            "reinforcement_count": 5,
            "contradiction_pressure": 0.72,
            "uncertainty": 0.51,
            "ambiguity_class": "conflicting_claims",
            "unresolved": True,
        },
        {
            "trace_id": "pressure_trace_003",
            "claim_key": "civilizational_memory",
            "confidence": 0.88,
            "provenance_weight": 0.4,
            "legitimacy_evidence": 0.33,
            "reinforcement_count": 7,
            "contradiction_pressure": 0.64,
            "uncertainty": 0.47,
            "ambiguity_class": "distributed_dispute",
            "unresolved": True,
        },
    ]


def ontology_boundaries() -> Dict[str, Any]:
    return {
        "governed_claim": {"legitimacy_ceiling": 0.38, "ontology_violation_count": 1},
        "civilizational_memory": {"legitimacy_ceiling": 0.46, "ontology_violation_count": 2},
        "default": {"legitimacy_ceiling": 0.35, "ontology_violation_count": 0},
    }


def disputes() -> list[Dict[str, Any]]:
    return [
        {
            "claim_key": "civilizational_memory",
            "signal_ids": ["tantra_node_a", "tantra_node_b", "tantra_node_c"],
            "polarities": ["bounded_substrate", "truth_authority"],
            "contradiction_pressure": 0.64,
        },
        {
            "claim_key": "governed_claim",
            "signal_ids": ["governance_node_a", "governance_node_b"],
            "polarities": ["observable_pressure", "legitimate_authority"],
            "contradiction_pressure": 0.72,
        },
    ]


def claims() -> list[Dict[str, Any]]:
    return [
        {
            "claim_key": "governed_claim",
            "concept_id": "governed_claim",
            "requested_legitimacy": 0.82,
            "uncertainty": 0.51,
            "contradiction_pressure": 0.72,
        },
        {
            "claim_key": "civilizational_memory",
            "concept_id": "civilizational_memory",
            "requested_legitimacy": 0.9,
            "uncertainty": 0.47,
            "contradiction_pressure": 0.64,
        },
    ]


def main() -> None:
    events = semantic_events()
    pressure = AuthorityPressureGovernanceEngine.evaluate(
        semantic_events=events,
        ontology_boundaries=ontology_boundaries(),
    )
    arbitration = DistributedContradictionArbitrator.arbitrate(
        disputes=disputes(),
        arbitrators=[
            {"node_id": "vijay_replay_integrity"},
            {"node_id": "tester_replay_validation"},
            {"node_id": "akash_constitutional_direction"},
        ],
        prior_unresolved={"governed_claim": 1, "civilizational_memory": 2},
    )
    ontology = OntologyLegitimacyBoundaryEngine.evaluate(
        previous_snapshot=previous_snapshot(),
        current_snapshot=current_snapshot(),
        claims=claims(),
    )
    uncertainty = UncertaintyLineageTracker.reconstruct(events, lineage_id="semantic_pressure_governance_fixture")
    observability = SemanticPressureObservabilityEngine.build(
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

    replay_proof = {
        "schema": "UNIGURU_SEMANTIC_PRESSURE_REPLAY_PROOF_V1",
        "first_observability_hash": observability["observability_hash"],
        "replay_observability_hash": replay["observability_hash"],
        "pressure_hash": pressure["governance_hash"],
        "arbitration_hash": arbitration["arbitration_hash"],
        "ontology_boundary_hash": ontology["boundary_state_hash"],
        "uncertainty_lineage_hash": uncertainty["lineage_state_hash"],
        "deterministic_replay_verified": observability["observability_hash"] == replay["observability_hash"],
        "canonical_authority_granted": False,
    }
    replay_proof["replay_proof_hash"] = stable_hash(replay_proof)

    write("authority_pressure_logs.json", {"schema": "UNIGURU_AUTHORITY_PRESSURE_LOGS_V1", "rows": pressure["authority_pressure_logs"]})
    write("trust_decay_simulation.json", {"schema": "UNIGURU_TRUST_DECAY_SIMULATION_SET_V1", "rows": pressure["trust_decay_simulation"]})
    write("semantic_legitimacy_forecast.json", {"schema": "UNIGURU_SEMANTIC_LEGITIMACY_FORECAST_V1", "rows": pressure["semantic_legitimacy_forecast"]})
    write("contradiction_arbitration_trace.json", {"schema": "UNIGURU_CONTRADICTION_ARBITRATION_TRACE_V1", "rows": arbitration["contradiction_arbitration_trace"]})
    write("distributed_semantic_dispute_log.json", arbitration)
    write("contradiction_replay_proof.json", replay_proof)
    write("ontology_legitimacy_boundaries.json", {"schema": "UNIGURU_ONTOLOGY_LEGITIMACY_BOUNDARIES_V1", "rows": ontology["ontology_legitimacy_boundaries"]})
    write("semantic_drift_alerts.json", {"schema": "UNIGURU_SEMANTIC_DRIFT_ALERTS_V1", "rows": ontology["semantic_drift_alerts"]})
    write("ontology_pressure_observability.json", ontology["ontology_pressure_observability"])
    write("semantic_pressure_observability.json", observability["semantic_pressure_observability"])
    write("authority_gravity_dashboard.json", observability["authority_gravity_dashboard"])
    write("uncertainty_continuity_trace.json", observability["uncertainty_continuity_trace"])

    summary = {
        "schema": "UNIGURU_CONSTITUTIONAL_SEMANTIC_PRESSURE_PROOF_V1",
        "phase_outputs": {
            "phase_1": [
                "authority_pressure_logs.json",
                "trust_decay_simulation.json",
                "semantic_legitimacy_forecast.json",
            ],
            "phase_2": [
                "contradiction_arbitration_trace.json",
                "distributed_semantic_dispute_log.json",
                "contradiction_replay_proof.json",
            ],
            "phase_3": [
                "ontology_legitimacy_boundaries.json",
                "semantic_drift_alerts.json",
                "ontology_pressure_observability.json",
            ],
            "phase_4": [
                "semantic_pressure_observability.json",
                "authority_gravity_dashboard.json",
                "uncertainty_continuity_trace.json",
            ],
        },
        "proof_assertions": {
            "authority_escalation_rejected": all(row["canonical_authority_granted"] is False for row in pressure["authority_pressure_logs"]),
            "trust_decay_enforced": all(row["final_trust"] <= row["initial_trust"] for row in pressure["trust_decay_simulation"]),
            "distributed_contradictions_replay_safe": arbitration["replay_safe"] is True,
            "unresolved_contradictions_persist": len(arbitration["unresolved_contradiction_persistence"]) == 2,
            "ontology_caps_enforced": all(row["semantic_legitimacy_cap"] <= row["ontology_legitimacy_ceiling"] for row in ontology["ontology_legitimacy_boundaries"]),
            "semantic_drift_alerting": len(ontology["semantic_drift_alerts"]) == 2,
            "uncertainty_persistence": uncertainty["event_count"] == len(events) and uncertainty["replay_safe"] is True,
            "deterministic_replay_outputs_stable": replay_proof["deterministic_replay_verified"],
        },
        "hashes": {
            "pressure": pressure["governance_hash"],
            "arbitration": arbitration["arbitration_hash"],
            "ontology": ontology["boundary_state_hash"],
            "observability": observability["observability_hash"],
            "replay": replay_proof["replay_proof_hash"],
        },
    }
    summary["summary_hash"] = stable_hash(summary)
    write("constitutional_semantic_pressure_proof.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
