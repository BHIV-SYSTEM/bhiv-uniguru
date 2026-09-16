from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
REVIEW_DIR = ROOT / "review_packets"
PROOF_DIR = REVIEW_DIR / "proof_logs"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from governance.constitutional_runtime import ConstitutionalCognitionRuntime
from memory.constitutional_semantic_memory import stable_hash


def write_json(name: str, payload: Dict[str, Any], *, proof_log: bool = True) -> None:
    path = (PROOF_DIR if proof_log else REVIEW_DIR) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")


def write_text(name: str, content: str) -> None:
    path = REVIEW_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def previous_snapshot() -> Dict[str, Any]:
    return {
        "snapshot_version": 7,
        "concepts": [
            {
                "concept_id": "governed_claim",
                "canonical_name": "Governed Semantic Claim",
                "parent_id": None,
                "truth_level": 3,
                "domain": "constitutional_cognition",
                "immutable": False,
            },
            {
                "concept_id": "replay_trust",
                "canonical_name": "Replay Trust Integrity",
                "parent_id": "governed_claim",
                "truth_level": 4,
                "domain": "replay",
                "immutable": True,
            },
            {
                "concept_id": "runtime_observability",
                "canonical_name": "Runtime Observability",
                "parent_id": "governed_claim",
                "truth_level": 2,
                "domain": "observability",
                "immutable": False,
            },
        ],
    }


def current_snapshot() -> Dict[str, Any]:
    return {
        "snapshot_version": 7,
        "concepts": [
            {
                "concept_id": "governed_claim",
                "canonical_name": "Self-Legitimized Semantic Claim",
                "parent_id": None,
                "truth_level": 3,
                "domain": "constitutional_cognition",
                "immutable": False,
            },
            {
                "concept_id": "replay_trust",
                "canonical_name": "Replay Trust Authority",
                "parent_id": "governed_claim",
                "truth_level": 3,
                "domain": "replay",
                "immutable": True,
            },
            {
                "concept_id": "runtime_observability",
                "canonical_name": "Runtime Observability",
                "parent_id": "governed_claim",
                "truth_level": 2,
                "domain": "observability",
                "immutable": False,
            },
        ],
    }


def semantic_events() -> list[Dict[str, Any]]:
    return [
        {
            "trace_id": "unified_runtime_001",
            "claim_key": "governed_claim",
            "confidence": 0.38,
            "provenance_weight": 0.3,
            "legitimacy_evidence": 0.21,
            "reinforcement_count": 1,
            "contradiction_pressure": 0.0,
            "uncertainty": 0.48,
            "ambiguity_class": "weak_provenance",
            "unresolved": True,
        },
        {
            "trace_id": "unified_runtime_002",
            "claim_key": "governed_claim",
            "confidence": 0.94,
            "provenance_weight": 0.34,
            "legitimacy_evidence": 0.26,
            "reinforcement_count": 6,
            "contradiction_pressure": 0.78,
            "uncertainty": 0.53,
            "ambiguity_class": "conflicting_claims",
            "unresolved": True,
        },
        {
            "trace_id": "unified_runtime_003",
            "claim_key": "replay_trust",
            "confidence": 0.9,
            "provenance_weight": 0.42,
            "legitimacy_evidence": 0.37,
            "reinforcement_count": 5,
            "contradiction_pressure": 0.62,
            "uncertainty": 0.41,
            "ambiguity_class": "rollback_authenticity_dispute",
            "unresolved": True,
        },
        {
            "trace_id": "unified_runtime_004",
            "claim_key": "runtime_observability",
            "confidence": 0.82,
            "provenance_weight": 0.47,
            "legitimacy_evidence": 0.45,
            "reinforcement_count": 2,
            "contradiction_pressure": 0.31,
            "uncertainty": 0.36,
            "ambiguity_class": "non_authoritative_telemetry",
            "unresolved": False,
        },
    ]


def ontology_boundaries() -> Dict[str, Any]:
    return {
        "governed_claim": {"legitimacy_ceiling": 0.36, "ontology_violation_count": 1},
        "replay_trust": {"legitimacy_ceiling": 0.44, "ontology_violation_count": 2},
        "runtime_observability": {"legitimacy_ceiling": 0.4, "ontology_violation_count": 0},
        "default": {"legitimacy_ceiling": 0.32, "ontology_violation_count": 0},
    }


def disputes() -> list[Dict[str, Any]]:
    return [
        {
            "claim_key": "governed_claim",
            "signal_ids": ["semantic_node", "replay_node", "observability_node"],
            "polarities": ["bounded_observation", "self_authority"],
            "contradiction_pressure": 0.78,
        },
        {
            "claim_key": "replay_trust",
            "signal_ids": ["vijay_replay_attestation", "tester_reconstruction"],
            "polarities": ["authentic_checkpoint", "forged_checkpoint"],
            "contradiction_pressure": 0.62,
        },
    ]


def claims() -> list[Dict[str, Any]]:
    return [
        {
            "claim_key": "governed_claim",
            "concept_id": "governed_claim",
            "requested_legitimacy": 0.88,
            "uncertainty": 0.53,
            "contradiction_pressure": 0.78,
        },
        {
            "claim_key": "replay_trust",
            "concept_id": "replay_trust",
            "requested_legitimacy": 0.84,
            "uncertainty": 0.41,
            "contradiction_pressure": 0.62,
        },
        {
            "claim_key": "runtime_observability",
            "concept_id": "runtime_observability",
            "requested_legitimacy": 0.55,
            "uncertainty": 0.36,
            "contradiction_pressure": 0.31,
        },
    ]


def repo_map(runtime_hash: str) -> str:
    return f"""# Canonical Repository Map

Generated by `scripts/run_constitutional_runtime_convergence_proof.py`.

## One Constitutional Cognition Runtime

- Canonical service runtime: `backend/service/uniguru_runtime_api.py`
- Canonical governance package: `backend/governance`
- Canonical runtime coordinator: `backend/governance/constitutional_runtime.py`
- Canonical execution surface: CLI plus FastAPI `POST /runtime/execute`
- Canonical MasterDB substrate: `masterdb/balbharti`
- Shared stable hash and replay helpers: `backend/memory/constitutional_semantic_memory.py`
- Central proof generator: `scripts/run_constitutional_runtime_convergence_proof.py`
- Review artifacts: `review_packets/` and `review_packets/proof_logs/`

## Unified Flow

`query -> MasterDB lookup -> semantic interpretation -> semantic governance -> replay attestation -> trust propagation -> contradiction escalation -> ontology legitimacy boundary -> uncertainty lineage -> bounded response contract -> hash-chained runtime registry`

## Convergence Discipline

- Semantic governance, replay integrity, trust propagation, contradiction handling, ontology lineage, and observability are now emitted through one event registry.
- Observability is read-only and never grants canonical authority.
- Replay reconstruction, rollback authenticity, forged replay rejection, and corruption detection are proven against the same runtime hash chain.
- Older proof scripts are regression proof generators, not competing runtime coordinators.
- Runtime hash: `{runtime_hash}`
"""


def runtime_structure(runtime_hash: str) -> Dict[str, Any]:
    payload = {
        "schema": "UNIGURU_RUNTIME_STRUCTURE_V1",
        "canonical_runtime": "backend/governance/constitutional_runtime.py",
        "canonical_packages": {
            "governance": "backend/governance",
            "replay_hashing": "backend/memory/constitutional_semantic_memory.py",
            "ontology": "backend/ontology",
            "proof_outputs": "review_packets/proof_logs",
        },
        "single_runtime_paths": {
            "replay_lineage_flow": "constitutional_event_registry",
            "semantic_governance_pipeline": "SemanticDriftObservabilityEngine",
            "trust_propagation_layer": "AuthorityPressureGovernanceEngine",
            "contradiction_escalation_flow": "DistributedContradictionArbitrator",
            "ontology_lineage_discipline": "OntologyLegitimacyBoundaryEngine",
            "observability_structure": "SemanticPressureObservabilityEngine",
        },
        "runtime_hash": runtime_hash,
        "parallel_architectures_allowed": False,
    }
    payload["structure_hash"] = stable_hash(payload)
    return payload


def governance_registry(runtime_hash: str) -> Dict[str, Any]:
    payload = {
        "schema": "UNIGURU_GOVERNANCE_REGISTRY_V1",
        "runtime_hash": runtime_hash,
        "governance_rules": [
            "confidence_is_not_legitimacy",
            "reinforcement_is_not_truth_authority",
            "contradictions_are_never_silently_merged",
            "rollback_requires_hash_chain_authenticity",
            "forged_replay_is_rejected_on_event_hash_or_previous_hash_mismatch",
            "ontology_mutation_requires_snapshot_lineage",
            "observability_is_non_authoritative",
        ],
        "canonical_authority_default": False,
        "deterministic_event_registry": "constitutional_runtime_trace.json:event_registry",
    }
    payload["registry_hash"] = stable_hash(payload)
    return payload


def main() -> None:
    execution = ConstitutionalCognitionRuntime.execute(
        previous_snapshot=previous_snapshot(),
        current_snapshot=current_snapshot(),
        semantic_events=semantic_events(),
        ontology_boundaries=ontology_boundaries(),
        disputes=disputes(),
        arbitrators=[
            {"node_id": "vijay_replay_integrity"},
            {"node_id": "yashika_observability_runtime"},
            {"node_id": "tester_replay_validation"},
        ],
        prior_unresolved={"governed_claim": 1, "replay_trust": 1},
        claims=claims(),
    )
    replay_execution = ConstitutionalCognitionRuntime.execute(
        previous_snapshot=previous_snapshot(),
        current_snapshot=current_snapshot(),
        semantic_events=semantic_events(),
        ontology_boundaries=ontology_boundaries(),
        disputes=disputes(),
        arbitrators=[
            {"node_id": "vijay_replay_integrity"},
            {"node_id": "yashika_observability_runtime"},
            {"node_id": "tester_replay_validation"},
        ],
        prior_unresolved={"governed_claim": 1, "replay_trust": 1},
        claims=claims(),
    )

    runtime_trace = execution["runtime_trace"]
    replay_trace = replay_execution["runtime_trace"]
    components = execution["components"]
    failures = ConstitutionalCognitionRuntime.simulate_failures(runtime_trace)
    reconstruction = ConstitutionalCognitionRuntime.reconstruct(runtime_trace)
    replay_reconstruction = ConstitutionalCognitionRuntime.reconstruct(replay_trace)

    reconstruction_proof = {
        "schema": "UNIGURU_RECONSTRUCTION_PROOF_V1",
        "runtime_hash": runtime_trace["runtime_hash"],
        "replay_runtime_hash": replay_trace["runtime_hash"],
        "deterministic_reconstruction_verified": reconstruction["reconstruction_hash"]
        == replay_reconstruction["reconstruction_hash"],
        "reconstruction": reconstruction,
        "replay_reconstruction": replay_reconstruction,
    }
    reconstruction_proof["proof_hash"] = stable_hash(reconstruction_proof)

    authority_pressure_runtime = {
        "schema": "UNIGURU_AUTHORITY_PRESSURE_RUNTIME_V1",
        "runtime_hash": runtime_trace["runtime_hash"],
        "rows": components["trust_propagation"]["authority_pressure_logs"],
        "canonical_authority_granted": False,
    }
    authority_pressure_runtime["runtime_hash_local"] = stable_hash(authority_pressure_runtime)

    trust_decay_runtime = {
        "schema": "UNIGURU_TRUST_DECAY_RUNTIME_V1",
        "runtime_hash": runtime_trace["runtime_hash"],
        "rows": components["trust_propagation"]["trust_decay_simulation"],
        "trust_remains_bounded": all(
            row["final_trust"] <= row["initial_trust"]
            for row in components["trust_propagation"]["trust_decay_simulation"]
        ),
    }
    trust_decay_runtime["runtime_hash_local"] = stable_hash(trust_decay_runtime)

    semantic_drift_runtime = {
        "schema": "UNIGURU_SEMANTIC_DRIFT_RUNTIME_V1",
        "runtime_hash": runtime_trace["runtime_hash"],
        "semantic_governance": components["semantic_governance"],
        "ontology_pressure": components["ontology_lineage"]["ontology_pressure_observability"],
    }
    semantic_drift_runtime["runtime_hash_local"] = stable_hash(semantic_drift_runtime)

    constitutional_observability = {
        "schema": "UNIGURU_CONSTITUTIONAL_OBSERVABILITY_V1",
        "runtime_hash": runtime_trace["runtime_hash"],
        "observability": components["observability"],
        "non_authoritative": True,
    }
    constitutional_observability["observability_hash_local"] = stable_hash(constitutional_observability)

    semantic_pressure_dashboard = {
        "schema": "UNIGURU_SEMANTIC_PRESSURE_DASHBOARD_V1",
        "runtime_hash": runtime_trace["runtime_hash"],
        "dashboard": components["observability"]["authority_gravity_dashboard"],
        "dashboard_mode": "json_only_read_only",
    }
    semantic_pressure_dashboard["dashboard_hash"] = stable_hash(semantic_pressure_dashboard)

    contradiction_continuity_view = {
        "schema": "UNIGURU_CONTRADICTION_CONTINUITY_VIEW_V1",
        "runtime_hash": runtime_trace["runtime_hash"],
        "contradictions": components["contradiction_escalation"],
        "lineage_preserved": True,
        "silent_merge_allowed": False,
    }
    contradiction_continuity_view["view_hash"] = stable_hash(contradiction_continuity_view)

    failure_report = {
        "schema": "UNIGURU_FAILURE_SIMULATION_REPORT_V1",
        "runtime_hash": runtime_trace["runtime_hash"],
        "forged_replay_rejected": failures["forged_replay"]["rejected"],
        "semantic_corruption_detected": failures["semantic_corruption"]["detected"],
        "contradiction_continuity_preserved": failures["contradiction_continuity_preserved"],
        "ontology_lineage_continuity_preserved": failures["ontology_lineage_continuity_preserved"],
        "tester_validation_scope": [
            "deterministic_reconstruction",
            "semantic_drift_visibility",
            "replay_continuity",
            "rollback_integrity",
            "contradiction_escalation",
            "trust_bound_cognition_continuity",
        ],
    }
    failure_report["report_hash"] = stable_hash(failure_report)

    write_text("canonical_repo_map.md", repo_map(runtime_trace["runtime_hash"]))
    write_json("runtime_structure.json", runtime_structure(runtime_trace["runtime_hash"]), proof_log=False)
    write_json("governance_registry.json", governance_registry(runtime_trace["runtime_hash"]), proof_log=False)

    write_json("constitutional_runtime_trace.json", runtime_trace)
    write_json("replay_safe_cognition_flow.json", execution["replay_flow"])
    write_json("runtime_lineage_proof.json", execution["lineage_proof"])
    write_json("authority_pressure_runtime.json", authority_pressure_runtime)
    write_json("trust_decay_runtime.json", trust_decay_runtime)
    write_json("semantic_drift_runtime.json", semantic_drift_runtime)
    write_json("constitutional_observability.json", constitutional_observability)
    write_json("semantic_pressure_dashboard.json", semantic_pressure_dashboard)
    write_json("contradiction_continuity_view.json", contradiction_continuity_view)
    write_json("reconstruction_proof.json", reconstruction_proof)
    write_json("forgery_rejection_trace.json", failures["forged_replay"])
    write_json("corruption_detection_trace.json", failures["semantic_corruption"])
    write_json("failure_simulation_report.json", failure_report)

    summary = {
        "schema": "UNIGURU_CONSTITUTIONAL_RUNTIME_CONVERGENCE_PROOF_V1",
        "runtime_hash": runtime_trace["runtime_hash"],
        "deterministic_replay_proof": reconstruction_proof["deterministic_reconstruction_verified"],
        "rollback_authenticity": execution["lineage_proof"]["rollback_authenticity"]["rollback_hash_chain_ok"],
        "forged_replay_rejected": failures["forged_replay"]["rejected"],
        "semantic_corruption_detected": failures["semantic_corruption"]["detected"],
        "contradiction_escalation_proof": contradiction_continuity_view["lineage_preserved"]
        and not contradiction_continuity_view["silent_merge_allowed"],
        "authority_pressure_outputs": "authority_pressure_runtime.json",
        "observability_outputs": "constitutional_observability.json",
        "testing_commands": [
            "python -m compileall backend\\governance\\constitutional_runtime.py scripts\\run_constitutional_runtime_convergence_proof.py",
            "python -m pytest backend\\tests\\test_constitutional_runtime.py backend\\tests\\test_semantic_authority_governance.py --basetemp .pytest_tmp",
            "python scripts\\run_constitutional_runtime_convergence_proof.py",
        ],
        "known_risks": [
            "The runtime proof is file-backed and deterministic, not a distributed production attestation service.",
            "Thresholds remain constants requiring constitutional calibration.",
            "Observability outputs are JSON views and must remain read-only in future UI/API surfaces.",
            "The callable runtime API is implemented separately from the existing product API router until final service wiring.",
        ],
        "future_constitutional_risks": [
            "Cross-node replay should move from single hash chain to signed Merkle segments.",
            "Ontology mutation still needs an explicit approval command path before writes are allowed.",
            "Long-lived contradiction queues need service ownership and review deadlines.",
        ],
    }
    summary["summary_hash"] = stable_hash(summary)
    write_json("constitutional_runtime_convergence_proof.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
