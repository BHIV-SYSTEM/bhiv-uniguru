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
    ContradictionEscalationGovernance,
    SemanticDriftObservabilityEngine,
    TrustBoundSemanticWeightingFramework,
    UncertaintyLineageTracker,
)


def write(name: str, payload: Dict[str, Any]) -> None:
    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    (PROOF_DIR / name).write_text(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")


def snapshots() -> tuple[Dict[str, Any], Dict[str, Any]]:
    previous = {
        "snapshot_version": 1,
        "concepts": [
            {
                "concept_id": "governed_claim",
                "canonical_name": "Governed Semantic Claim",
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
                "concept_id": "governed_claim",
                "canonical_name": "Self-Legitimized Semantic Claim",
                "parent_id": None,
                "truth_level": 3,
                "domain": "core",
                "immutable": False,
            }
        ],
    }
    return previous, current


def semantic_events() -> list[Dict[str, Any]]:
    return [
        {
            "trace_id": "authority_pressure_a",
            "claim_key": "governed_claim",
            "confidence": 0.4,
            "reinforcement_count": 1,
            "contradiction_pressure": 0.0,
            "uncertainty": 0.46,
            "ambiguity_class": "interpretive_or_weak_evidence_zone",
            "unresolved": True,
        },
        {
            "trace_id": "authority_pressure_b",
            "claim_key": "governed_claim",
            "confidence": 0.93,
            "reinforcement_count": 6,
            "contradiction_pressure": 0.8,
            "uncertainty": 0.53,
            "ambiguity_class": "conflicting_claims",
            "unresolved": True,
        },
    ]


def main() -> None:
    previous, current = snapshots()
    events = semantic_events()
    drift = SemanticDriftObservabilityEngine.observe(
        previous_snapshot=previous,
        current_snapshot=current,
        semantic_events=events,
    )
    contradiction = ContradictionEscalationGovernance.evaluate(
        contradictions=[
            {
                "claim_key": "governed_claim",
                "signal_ids": ["source_signal_a", "source_signal_b"],
                "polarities": ["affirmative", "negative"],
            }
        ],
        signals=[{"signal_id": "source_signal_a"}, {"signal_id": "source_signal_b"}],
        prior_unresolved_count=1,
        quorum_required=2,
    )
    weighting = TrustBoundSemanticWeightingFramework.score(
        confidence=0.93,
        prior_confidence=0.4,
        provenance_weight=0.34,
        legitimacy_evidence=0.26,
        reinforcement_count=6,
        contradiction_pressure=0.8,
        uncertainty=0.53,
    )
    uncertainty = UncertaintyLineageTracker.reconstruct(events, lineage_id="semantic_authority_pressure_fixture")

    summary = {
        "schema": "UNIGURU_SEMANTIC_AUTHORITY_GOVERNANCE_PROOF_V1",
        "semantic_drift_telemetry": drift,
        "contradiction_replay_audit": contradiction,
        "trust_bound_weighting": weighting,
        "uncertainty_lineage_reconstruction": uncertainty,
        "proof_assertions": {
            "confidence_inflation_rejected": weighting["confidence_inflation_detected"]
            and weighting["boundary_decision"] == "REJECT_LEGITIMACY_ESCALATION",
            "authority_accumulation_detected": drift["reinforcement_pressure"]["authority_accumulation_detected"],
            "ontology_drift_audited": drift["ontology_drift"]["accepted"] is False,
            "contradiction_escalated": contradiction["lifecycle_state"] == "PERSISTENT_UNRESOLVED",
            "uncertainty_lineage_replay_safe": uncertainty["replay_safe"],
            "canonical_authority_never_granted": drift["canonical_authority_granted"] is False
            and contradiction["canonical_authority_granted"] is False
            and weighting["canonical_authority_granted"] is False,
        },
    }

    write("semantic_authority_governance_proof.json", summary)
    write("semantic_drift_telemetry.json", drift)
    write("contradiction_replay_audit.json", contradiction)
    write("trust_bound_weighting.json", weighting)
    write("uncertainty_lineage_reconstruction.json", uncertainty)
    print(json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
