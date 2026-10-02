from __future__ import annotations

from typing import Any, Dict, List, Optional

from governance.semantic_authority import (
    AuthorityPressureGovernanceEngine,
    DistributedContradictionArbitrator,
    OntologyLegitimacyBoundaryEngine,
    SemanticDriftObservabilityEngine,
    SemanticPressureObservabilityEngine,
    UncertaintyLineageTracker,
)
from memory.constitutional_semantic_memory import stable_hash


def _hash_named_components(components: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    return {name: stable_hash(payload) for name, payload in sorted(components.items())}


def _event(
    *,
    index: int,
    event_type: str,
    component: str,
    payload_hash: str,
    previous_event_hash: Optional[str],
    decision: str,
) -> Dict[str, Any]:
    row = {
        "index": index,
        "event_type": event_type,
        "component": component,
        "payload_hash": payload_hash,
        "previous_event_hash": previous_event_hash,
        "decision": decision,
        "canonical_authority_granted": False,
    }
    row["event_hash"] = stable_hash(row)
    return row


def verify_event_chain(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    previous: Optional[str] = None
    failures: List[Dict[str, Any]] = []
    for row in events:
        expected = stable_hash({key: value for key, value in row.items() if key != "event_hash"})
        if row.get("previous_event_hash") != previous:
            failures.append(
                {
                    "index": row.get("index"),
                    "type": "previous_hash_mismatch",
                    "expected_previous_hash": previous,
                    "actual_previous_hash": row.get("previous_event_hash"),
                }
            )
        if row.get("event_hash") != expected:
            failures.append(
                {
                    "index": row.get("index"),
                    "type": "event_hash_mismatch",
                    "expected_event_hash": expected,
                    "actual_event_hash": row.get("event_hash"),
                }
            )
        previous = row.get("event_hash")
    return {
        "hash_chain_ok": not failures,
        "failure_count": len(failures),
        "failures": failures,
        "last_event_hash": previous,
    }


class ConstitutionalCognitionRuntime:
    """One deterministic coordinator for governance, replay, trust, and observability."""

    @classmethod
    def execute(
        cls,
        *,
        previous_snapshot: Dict[str, Any],
        current_snapshot: Dict[str, Any],
        semantic_events: List[Dict[str, Any]],
        ontology_boundaries: Dict[str, Any],
        disputes: List[Dict[str, Any]],
        arbitrators: List[Dict[str, Any]],
        prior_unresolved: Dict[str, int],
        claims: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        semantic_governance = SemanticDriftObservabilityEngine.observe(
            previous_snapshot=previous_snapshot,
            current_snapshot=current_snapshot,
            semantic_events=semantic_events,
        )
        trust_pressure = AuthorityPressureGovernanceEngine.evaluate(
            semantic_events=semantic_events,
            ontology_boundaries=ontology_boundaries,
        )
        contradiction = DistributedContradictionArbitrator.arbitrate(
            disputes=disputes,
            arbitrators=arbitrators,
            prior_unresolved=prior_unresolved,
        )
        ontology = OntologyLegitimacyBoundaryEngine.evaluate(
            previous_snapshot=previous_snapshot,
            current_snapshot=current_snapshot,
            claims=claims,
        )
        uncertainty = UncertaintyLineageTracker.reconstruct(
            semantic_events,
            lineage_id="constitutional_runtime_uncertainty_lineage",
        )
        observability = SemanticPressureObservabilityEngine.build(
            pressure_governance=trust_pressure,
            contradiction_arbitration=contradiction,
            ontology_boundaries=ontology,
            uncertainty_lineage=uncertainty,
        )

        components = {
            "semantic_governance": semantic_governance,
            "trust_propagation": trust_pressure,
            "contradiction_escalation": contradiction,
            "ontology_lineage": ontology,
            "uncertainty_lineage": uncertainty,
            "observability": observability,
        }
        component_hashes = _hash_named_components(components)
        registry = cls._build_event_registry(component_hashes)
        registry_verification = verify_event_chain(registry)

        runtime_trace = {
            "schema": "UNIGURU_CONSTITUTIONAL_COGNITION_RUNTIME_TRACE_V1",
            "runtime_id": "constitutional_cognition_runtime_v1",
            "repo_convergence": {
                "single_governance_package": "backend/governance",
                "single_replay_lineage_flow": "constitutional_event_registry",
                "single_trust_layer": "AuthorityPressureGovernanceEngine",
                "single_observability_layer": "SemanticPressureObservabilityEngine",
                "no_parallel_authority_path": True,
            },
            "component_hashes": component_hashes,
            "event_registry": registry,
            "event_registry_verification": registry_verification,
            "canonical_authority_granted": False,
        }
        runtime_trace["runtime_hash"] = stable_hash(runtime_trace)

        replay_flow = {
            "schema": "UNIGURU_REPLAY_SAFE_COGNITION_FLOW_V1",
            "flow": [
                "semantic_event_ingestion",
                "semantic_governance_observation",
                "trust_bound_pressure_scoring",
                "contradiction_arbitration",
                "ontology_legitimacy_boundary",
                "uncertainty_lineage_reconstruction",
                "read_only_observability",
                "event_registry_attestation",
            ],
            "event_registry_hash": stable_hash(registry),
            "last_event_hash": registry_verification["last_event_hash"],
            "hash_chain_ok": registry_verification["hash_chain_ok"],
            "replay_safe": registry_verification["hash_chain_ok"],
            "canonical_authority_granted": False,
        }
        replay_flow["flow_hash"] = stable_hash(replay_flow)

        lineage_proof = cls._lineage_proof(registry, runtime_trace)

        return {
            "runtime_trace": runtime_trace,
            "replay_flow": replay_flow,
            "lineage_proof": lineage_proof,
            "components": components,
            "component_hashes": component_hashes,
        }

    @staticmethod
    def reconstruct(runtime_trace: Dict[str, Any]) -> Dict[str, Any]:
        events = runtime_trace.get("event_registry") or []
        verification = verify_event_chain(events)
        payload = {
            "schema": "UNIGURU_DETERMINISTIC_RUNTIME_RECONSTRUCTION_V1",
            "runtime_id": runtime_trace.get("runtime_id"),
            "event_count": len(events),
            "component_hashes": runtime_trace.get("component_hashes") or {},
            "hash_chain_ok": verification["hash_chain_ok"],
            "last_event_hash": verification["last_event_hash"],
            "canonical_authority_granted": False,
        }
        payload["reconstruction_hash"] = stable_hash(payload)
        return payload

    @classmethod
    def simulate_failures(cls, runtime_trace: Dict[str, Any]) -> Dict[str, Any]:
        events = [dict(row) for row in runtime_trace.get("event_registry") or []]
        forged = [dict(row) for row in events]
        corrupted = [dict(row) for row in events]

        if forged:
            forged[-1]["previous_event_hash"] = "forged_previous_hash"
        if corrupted:
            corrupted[1]["payload_hash"] = "corrupted_payload_hash"

        forged_verification = verify_event_chain(forged)
        corrupted_verification = verify_event_chain(corrupted)
        payload = {
            "schema": "UNIGURU_RUNTIME_FAILURE_SIMULATION_V1",
            "forged_replay": {
                "accepted": forged_verification["hash_chain_ok"],
                "rejected": not forged_verification["hash_chain_ok"],
                "verification": forged_verification,
            },
            "semantic_corruption": {
                "detected": not corrupted_verification["hash_chain_ok"],
                "verification": corrupted_verification,
            },
            "contradiction_continuity_preserved": any(
                row.get("component") == "contradiction_escalation" for row in events
            ),
            "ontology_lineage_continuity_preserved": any(
                row.get("component") == "ontology_lineage" for row in events
            ),
        }
        payload["failure_simulation_hash"] = stable_hash(payload)
        return payload

    @staticmethod
    def _build_event_registry(component_hashes: Dict[str, str]) -> List[Dict[str, Any]]:
        order = [
            ("runtime_convergence_declared", "runtime_structure", "DECLARE_SINGLE_RUNTIME"),
            ("semantic_governance_observed", "semantic_governance", "OBSERVE_WITHOUT_AUTHORITY"),
            ("trust_pressure_propagated", "trust_propagation", "PROPAGATE_BOUNDED_TRUST"),
            ("contradiction_escalated", "contradiction_escalation", "PERSIST_AND_ESCALATE"),
            ("ontology_lineage_checked", "ontology_lineage", "ENFORCE_LEGITIMACY_CAP"),
            ("uncertainty_lineage_reconstructed", "uncertainty_lineage", "PRESERVE_UNCERTAINTY"),
            ("observability_emitted", "observability", "EMIT_NON_AUTHORITATIVE_TELEMETRY"),
        ]
        events: List[Dict[str, Any]] = []
        previous: Optional[str] = None
        for index, (event_type, component, decision) in enumerate(order):
            payload_hash = component_hashes.get(component) or stable_hash({"component": component})
            row = _event(
                index=index,
                event_type=event_type,
                component=component,
                payload_hash=payload_hash,
                previous_event_hash=previous,
                decision=decision,
            )
            events.append(row)
            previous = row["event_hash"]
        return events

    @staticmethod
    def _lineage_proof(registry: List[Dict[str, Any]], runtime_trace: Dict[str, Any]) -> Dict[str, Any]:
        target = registry[3]["event_hash"] if len(registry) > 3 else None
        rollback_events = [row for row in registry if target is None or row["index"] <= 3]
        rollback_verification = verify_event_chain(rollback_events)
        payload = {
            "schema": "UNIGURU_RUNTIME_LINEAGE_PROOF_V1",
            "runtime_hash": runtime_trace["runtime_hash"],
            "registry_hash": stable_hash(registry),
            "forward_verification": verify_event_chain(registry),
            "rollback_authenticity": {
                "target_event_hash": target,
                "rollback_event_count": len(rollback_events),
                "rollback_hash_chain_ok": rollback_verification["hash_chain_ok"],
                "rollback_last_event_hash": rollback_verification["last_event_hash"],
            },
            "lineage_disciplines": {
                "semantic_governance": "hash_chained",
                "trust_propagation": "bounded_by_legitimacy_ceiling",
                "contradiction_escalation": "persistent_unresolved_audit",
                "ontology_lineage": "mutation_sensitive",
                "observability": "non_authoritative",
            },
        }
        payload["lineage_proof_hash"] = stable_hash(payload)
        return payload
