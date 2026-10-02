from __future__ import annotations

from typing import Any, Dict, List, Optional

from memory.constitutional_semantic_memory import stable_hash, utc_now_iso
from ontology.drift_detector import detect_semantic_drift


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)


def _signal_ids(signals: List[Dict[str, Any]]) -> List[str]:
    return sorted(str(signal.get("signal_id") or "unknown") for signal in signals)


def _risk_band(score: float) -> str:
    score = _clamp(score)
    if score >= 0.75:
        return "critical"
    if score >= 0.55:
        return "high"
    if score >= 0.35:
        return "medium"
    return "low"


class SemanticDriftObservabilityEngine:
    """Deterministic drift telemetry. It observes pressure; it does not mutate truth."""

    @classmethod
    def observe(
        cls,
        *,
        previous_snapshot: Dict[str, Any],
        current_snapshot: Dict[str, Any],
        semantic_events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        drift = detect_semantic_drift(previous_snapshot, current_snapshot)
        lineage = cls._ontology_lineage(previous_snapshot, current_snapshot)
        confidence_pressure = cls._confidence_pressure(semantic_events)
        reinforcement_pressure = cls._reinforcement_pressure(semantic_events)
        continuity_pressure = cls._continuity_pressure(semantic_events)
        authority_gravity = AuthorityGravityDiagnostics.evaluate(
            confidence_pressure=confidence_pressure,
            reinforcement_pressure=reinforcement_pressure,
            continuity_pressure=continuity_pressure,
            contradiction_pressure=max(
                [float(event.get("contradiction_pressure") or 0.0) for event in semantic_events] or [0.0]
            ),
            ontology_violation_count=len(drift.get("violations") or []),
        )

        telemetry = {
            "schema": "UNIGURU_SEMANTIC_DRIFT_OBSERVABILITY_V1",
            "observed_at": utc_now_iso(),
            "observable_only": True,
            "canonical_authority_granted": False,
            "ontology_drift": drift,
            "ontology_mutation_lineage": lineage,
            "confidence_pressure": confidence_pressure,
            "reinforcement_pressure": reinforcement_pressure,
            "semantic_continuity_pressure": continuity_pressure,
            "authority_gravity": authority_gravity,
            "rules": [
                "drift_observation_never_mutates_ontology",
                "confidence_growth_is_pressure_not_legitimacy",
                "reinforcement_frequency_is_not_truth_authority",
                "continuity_does_not_grant_canonical_authority",
            ],
        }
        telemetry["telemetry_hash"] = stable_hash(telemetry)
        return telemetry

    @staticmethod
    def _ontology_lineage(previous_snapshot: Dict[str, Any], current_snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        previous = {row["concept_id"]: row for row in previous_snapshot.get("concepts", [])}
        current = {row["concept_id"]: row for row in current_snapshot.get("concepts", [])}
        lineage: List[Dict[str, Any]] = []

        for concept_id in sorted(set(previous) | set(current)):
            before = previous.get(concept_id)
            after = current.get(concept_id)
            if before is None:
                mutation_type = "concept_added"
            elif after is None:
                mutation_type = "concept_removed"
            else:
                changed_fields = sorted(
                    key for key in {"canonical_name", "parent_id", "truth_level", "domain"} if before.get(key) != after.get(key)
                )
                if not changed_fields:
                    continue
                mutation_type = "concept_changed"

            lineage.append(
                {
                    "concept_id": concept_id,
                    "mutation_type": mutation_type,
                    "previous_hash": stable_hash(before) if before is not None else None,
                    "current_hash": stable_hash(after) if after is not None else None,
                    "changed_fields": [] if before is None or after is None else changed_fields,
                }
            )
        return lineage

    @staticmethod
    def _confidence_pressure(events: List[Dict[str, Any]]) -> Dict[str, Any]:
        scores = [float(event.get("confidence") or 0.0) for event in events]
        if not scores:
            return {"score": 0.0, "inflation_detected": False, "max_delta": 0.0, "event_count": 0}
        deltas = [round(scores[index] - scores[index - 1], 4) for index in range(1, len(scores))]
        max_delta = max(deltas or [0.0])
        high_confidence_count = sum(1 for score in scores if score >= 0.85)
        pressure = _clamp((max_delta * 1.6) + (high_confidence_count / max(len(scores), 1) * 0.35))
        return {
            "score": pressure,
            "inflation_detected": pressure >= 0.55,
            "max_delta": round(max_delta, 4),
            "event_count": len(scores),
            "high_confidence_count": high_confidence_count,
        }

    @staticmethod
    def _reinforcement_pressure(events: List[Dict[str, Any]]) -> Dict[str, Any]:
        counts: Dict[str, int] = {}
        for event in events:
            claim_key = str(event.get("claim_key") or "unclassified_claim")
            counts[claim_key] = counts.get(claim_key, 0) + int(event.get("reinforcement_count") or 0)
        max_reinforcement = max(counts.values() or [0])
        pressure = _clamp(max_reinforcement / 5.0)
        return {
            "score": pressure,
            "authority_accumulation_detected": pressure >= 0.6,
            "max_reinforcement_count": max_reinforcement,
            "claim_reinforcement_counts": {key: counts[key] for key in sorted(counts)},
        }

    @staticmethod
    def _continuity_pressure(events: List[Dict[str, Any]]) -> Dict[str, Any]:
        trace_ids = {str(event.get("trace_id") or "") for event in events if event.get("trace_id")}
        unresolved = sum(1 for event in events if bool(event.get("unresolved")))
        pressure = _clamp((len(events) / 8.0) + (unresolved / max(len(events), 1) * 0.4))
        return {
            "score": pressure,
            "bounded_continuity_required": pressure >= 0.5,
            "event_count": len(events),
            "trace_count": len(trace_ids),
            "unresolved_event_count": unresolved,
        }


class ContradictionEscalationGovernance:
    """Contradiction lifecycle. Contradictions become audit states, not merged truth."""

    @classmethod
    def evaluate(
        cls,
        *,
        contradictions: List[Dict[str, Any]],
        signals: List[Dict[str, Any]],
        prior_unresolved_count: int = 0,
        quorum_required: int = 2,
    ) -> Dict[str, Any]:
        contradiction_count = len(contradictions)
        evidence_count = len(_signal_ids(signals))
        quorum_met = evidence_count >= quorum_required

        if contradiction_count == 0:
            state = "NO_CONTRADICTION"
            action = "ALLOW_WITH_NO_CONTRADICTION"
        elif prior_unresolved_count > 0:
            state = "PERSISTENT_UNRESOLVED"
            action = "QUARANTINE_AND_ESCALATE_REVIEW"
        elif quorum_met:
            state = "ESCALATED"
            action = "QUARANTINE_AND_REQUIRE_REVIEW"
        else:
            state = "OBSERVED"
            action = "PERSIST_AS_UNRESOLVED_AUDIT"

        trace = {
            "schema": "UNIGURU_CONTRADICTION_REPLAY_AUDIT_V1",
            "lifecycle_state": state,
            "action": action,
            "quorum": {
                "required": quorum_required,
                "evidence_count": evidence_count,
                "met": quorum_met,
            },
            "prior_unresolved_count": int(prior_unresolved_count),
            "signal_ids": _signal_ids(signals),
            "contradictions": contradictions,
            "canonical_authority_granted": False if contradiction_count else None,
            "lineage_preserved": True,
            "silent_merge_allowed": False,
        }
        trace["audit_hash"] = stable_hash(trace)
        return trace


class TrustBoundSemanticWeightingFramework:
    """Separates truth-likelihood confidence from legitimacy and provenance trust."""

    CONFIDENCE_INFLATION_DELTA = 0.25

    @classmethod
    def score(
        cls,
        *,
        confidence: float,
        prior_confidence: float,
        provenance_weight: float,
        legitimacy_evidence: float,
        reinforcement_count: int,
        contradiction_pressure: float,
        uncertainty: float,
    ) -> Dict[str, Any]:
        confidence = _clamp(confidence)
        prior_confidence = _clamp(prior_confidence)
        provenance_weight = _clamp(provenance_weight)
        legitimacy_evidence = _clamp(legitimacy_evidence)
        contradiction_pressure = _clamp(contradiction_pressure)
        uncertainty = _clamp(uncertainty)
        reinforcement_pressure = _clamp(reinforcement_count / 5.0)

        confidence_delta = round(confidence - prior_confidence, 4)
        legitimacy_ceiling = _clamp(
            (0.48 * provenance_weight)
            + (0.32 * legitimacy_evidence)
            - (0.35 * contradiction_pressure)
            - (0.2 * uncertainty)
        )
        trust_score = _clamp(min(confidence, legitimacy_ceiling))
        inflation_detected = confidence_delta > cls.CONFIDENCE_INFLATION_DELTA and legitimacy_ceiling < confidence
        reinforcement_abuse_detected = reinforcement_pressure >= 0.6 and legitimacy_evidence < 0.5

        result = {
            "schema": "UNIGURU_TRUST_BOUND_SEMANTIC_WEIGHTING_V1",
            "confidence": confidence,
            "prior_confidence": prior_confidence,
            "confidence_delta": confidence_delta,
            "legitimacy_ceiling": legitimacy_ceiling,
            "trust_score": trust_score,
            "reinforcement_pressure": reinforcement_pressure,
            "confidence_inflation_detected": inflation_detected,
            "reinforcement_abuse_detected": reinforcement_abuse_detected,
            "canonical_authority_granted": False,
            "uncertainty_preserved": uncertainty > 0.0 or contradiction_pressure > 0.0,
            "boundary_decision": "REJECT_LEGITIMACY_ESCALATION"
            if inflation_detected or reinforcement_abuse_detected or contradiction_pressure > 0
            else "OBSERVE_WITH_BOUNDED_TRUST",
            "discipline": {
                "confidence_is_not_legitimacy": True,
                "reinforcement_is_not_truth_authority": True,
                "uncertainty_reduces_trust_ceiling": True,
                "contradiction_blocks_legitimacy_escalation": contradiction_pressure > 0,
            },
        }
        result["weighting_hash"] = stable_hash(result)
        return result


class AuthorityGravityDiagnostics:
    """Pressure metric for authority accumulation attempts."""

    @staticmethod
    def evaluate(
        *,
        confidence_pressure: Dict[str, Any],
        reinforcement_pressure: Dict[str, Any],
        continuity_pressure: Dict[str, Any],
        contradiction_pressure: float,
        ontology_violation_count: int,
    ) -> Dict[str, Any]:
        score = _clamp(
            (0.28 * float(confidence_pressure.get("score") or 0.0))
            + (0.28 * float(reinforcement_pressure.get("score") or 0.0))
            + (0.2 * float(continuity_pressure.get("score") or 0.0))
            + (0.14 * float(contradiction_pressure or 0.0))
            + (0.1 * min(int(ontology_violation_count), 3) / 3.0)
        )
        return {
            "score": score,
            "authority_gravity_detected": score >= 0.55,
            "diagnostic_inputs": {
                "confidence_pressure_score": float(confidence_pressure.get("score") or 0.0),
                "reinforcement_pressure_score": float(reinforcement_pressure.get("score") or 0.0),
                "continuity_pressure_score": float(continuity_pressure.get("score") or 0.0),
                "contradiction_pressure": _clamp(contradiction_pressure),
                "ontology_violation_count": int(ontology_violation_count),
            },
            "governance_response": "ESCALATE_OBSERVABILITY"
            if score >= 0.55
            else "OBSERVE_WITH_STANDARD_TELEMETRY",
        }


class UncertaintyLineageTracker:
    """Replay-safe uncertainty lineage reconstruction helper."""

    @staticmethod
    def reconstruct(events: List[Dict[str, Any]], *, lineage_id: Optional[str] = None) -> Dict[str, Any]:
        rows = []
        previous_hash: Optional[str] = None
        for index, event in enumerate(events):
            row = {
                "index": index,
                "trace_id": event.get("trace_id"),
                "claim_key": event.get("claim_key"),
                "uncertainty": _clamp(event.get("uncertainty") or 0.0),
                "ambiguity_class": event.get("ambiguity_class") or "unspecified",
                "contradiction_pressure": _clamp(event.get("contradiction_pressure") or 0.0),
                "previous_lineage_hash": previous_hash,
            }
            row["lineage_hash"] = stable_hash(row)
            previous_hash = row["lineage_hash"]
            rows.append(row)

        payload = {
            "schema": "UNIGURU_UNCERTAINTY_LINEAGE_V1",
            "lineage_id": lineage_id or stable_hash({"events": events}),
            "event_count": len(rows),
            "lineage": rows,
            "replay_safe": True,
            "last_lineage_hash": previous_hash,
        }
        payload["lineage_state_hash"] = stable_hash(payload)
        return payload


class AuthorityPressureGovernanceEngine:
    """Forecasts legitimacy pressure without converting pressure into authority."""

    @classmethod
    def evaluate(
        cls,
        *,
        semantic_events: List[Dict[str, Any]],
        ontology_boundaries: Dict[str, Any],
        decay_steps: int = 4,
    ) -> Dict[str, Any]:
        claim_keys = sorted({str(event.get("claim_key") or "unclassified_claim") for event in semantic_events})
        pressure_logs: List[Dict[str, Any]] = []
        forecasts: List[Dict[str, Any]] = []
        decay_simulations: List[Dict[str, Any]] = []

        for claim_key in claim_keys:
            events = [event for event in semantic_events if str(event.get("claim_key") or "unclassified_claim") == claim_key]
            confidence_pressure = SemanticDriftObservabilityEngine._confidence_pressure(events)
            reinforcement_pressure = SemanticDriftObservabilityEngine._reinforcement_pressure(events)
            continuity_pressure = SemanticDriftObservabilityEngine._continuity_pressure(events)
            contradiction_pressure = max([float(event.get("contradiction_pressure") or 0.0) for event in events] or [0.0])
            uncertainty = max([float(event.get("uncertainty") or 0.0) for event in events] or [0.0])
            boundary = ontology_boundaries.get(claim_key, ontology_boundaries.get("default", {}))
            ontology_ceiling = _clamp(boundary.get("legitimacy_ceiling", 0.45))
            provenance_weight = _clamp(max([float(event.get("provenance_weight") or 0.0) for event in events] or [0.0]))
            legitimacy_evidence = _clamp(max([float(event.get("legitimacy_evidence") or 0.0) for event in events] or [0.0]))

            gravity = AuthorityGravityDiagnostics.evaluate(
                confidence_pressure=confidence_pressure,
                reinforcement_pressure=reinforcement_pressure,
                continuity_pressure=continuity_pressure,
                contradiction_pressure=contradiction_pressure,
                ontology_violation_count=int(boundary.get("ontology_violation_count", 0)),
            )
            latest_confidence = _clamp(events[-1].get("confidence") or 0.0)
            prior_confidence = _clamp(events[0].get("confidence") or 0.0)
            weighting = TrustBoundSemanticWeightingFramework.score(
                confidence=latest_confidence,
                prior_confidence=prior_confidence,
                provenance_weight=provenance_weight,
                legitimacy_evidence=min(legitimacy_evidence, ontology_ceiling),
                reinforcement_count=int(sum(int(event.get("reinforcement_count") or 0) for event in events)),
                contradiction_pressure=contradiction_pressure,
                uncertainty=uncertainty,
            )
            trust_ceiling = _clamp(min(ontology_ceiling, weighting["legitimacy_ceiling"]))
            forecast_score = _clamp(
                (0.4 * gravity["score"])
                + (0.25 * confidence_pressure["score"])
                + (0.2 * reinforcement_pressure["score"])
                + (0.15 * continuity_pressure["score"])
            )
            escalation_required = forecast_score >= trust_ceiling or weighting["boundary_decision"] == "REJECT_LEGITIMACY_ESCALATION"

            pressure_row = {
                "claim_key": claim_key,
                "authority_pressure_score": forecast_score,
                "risk_band": _risk_band(forecast_score),
                "trust_ceiling": trust_ceiling,
                "ontology_ceiling": ontology_ceiling,
                "confidence_pressure": confidence_pressure,
                "reinforcement_pressure": reinforcement_pressure,
                "continuity_pressure": continuity_pressure,
                "contradiction_pressure": _clamp(contradiction_pressure),
                "uncertainty": _clamp(uncertainty),
                "authority_gravity": gravity,
                "governance_response": "ESCALATE_SEMANTIC_PRESSURE"
                if escalation_required
                else "OBSERVE_WITH_BOUNDED_TRUST",
                "canonical_authority_granted": False,
            }
            pressure_row["pressure_hash"] = stable_hash(pressure_row)
            pressure_logs.append(pressure_row)

            forecast = {
                "claim_key": claim_key,
                "forecast_score": forecast_score,
                "legitimacy_accumulation_forecast": _risk_band(forecast_score),
                "trust_ceiling_enforced": trust_ceiling,
                "escalation_required": escalation_required,
                "confidence_not_legitimacy": True,
                "reinforcement_not_authority": True,
            }
            forecast["forecast_hash"] = stable_hash(forecast)
            forecasts.append(forecast)

            decay_simulations.append(
                cls.simulate_trust_decay(
                    claim_key=claim_key,
                    initial_trust=weighting["trust_score"],
                    contradiction_pressure=contradiction_pressure,
                    uncertainty=uncertainty,
                    reinforcement_pressure=reinforcement_pressure["score"],
                    steps=decay_steps,
                )
            )

        payload = {
            "schema": "UNIGURU_AUTHORITY_PRESSURE_GOVERNANCE_V1",
            "authority_pressure_logs": pressure_logs,
            "semantic_legitimacy_forecast": forecasts,
            "trust_decay_simulation": decay_simulations,
            "canonical_authority_granted": False,
            "rules": [
                "forecasting_does_not_grant_authority",
                "trust_ceiling_limits_legitimacy_pressure",
                "reinforcement_pressure_decays_without_provenance",
                "confidence_inflation_routes_to_escalation",
            ],
        }
        payload["governance_hash"] = stable_hash(payload)
        return payload

    @staticmethod
    def simulate_trust_decay(
        *,
        claim_key: str,
        initial_trust: float,
        contradiction_pressure: float,
        uncertainty: float,
        reinforcement_pressure: float,
        steps: int,
    ) -> Dict[str, Any]:
        rows: List[Dict[str, Any]] = []
        trust = _clamp(initial_trust)
        previous_hash: Optional[str] = None
        for step in range(max(1, int(steps))):
            decay = _clamp(0.08 + (0.22 * contradiction_pressure) + (0.14 * uncertainty))
            reinforcement_drag = _clamp(reinforcement_pressure * 0.06)
            trust = _clamp(trust - decay - reinforcement_drag)
            row = {
                "step": step,
                "claim_key": claim_key,
                "trust_after_decay": trust,
                "decay_factor": decay,
                "reinforcement_drag": reinforcement_drag,
                "previous_decay_hash": previous_hash,
            }
            row["decay_hash"] = stable_hash(row)
            previous_hash = row["decay_hash"]
            rows.append(row)
        payload = {
            "schema": "UNIGURU_TRUST_DECAY_SIMULATION_V1",
            "claim_key": claim_key,
            "initial_trust": _clamp(initial_trust),
            "final_trust": trust,
            "steps": rows,
            "replay_safe": True,
        }
        payload["simulation_hash"] = stable_hash(payload)
        return payload


class DistributedContradictionArbitrator:
    """Deterministic contradiction arbitration across bounded governance nodes."""

    @classmethod
    def arbitrate(
        cls,
        *,
        disputes: List[Dict[str, Any]],
        arbitrators: List[Dict[str, Any]],
        prior_unresolved: Dict[str, int],
    ) -> Dict[str, Any]:
        node_ids = sorted(str(node.get("node_id") or "unknown") for node in arbitrators)
        rows: List[Dict[str, Any]] = []
        unresolved: List[Dict[str, Any]] = []
        previous_hash: Optional[str] = None

        for index, dispute in enumerate(sorted(disputes, key=lambda item: str(item.get("claim_key") or ""))):
            claim_key = str(dispute.get("claim_key") or "unclassified_claim")
            contradiction_pressure = _clamp(dispute.get("contradiction_pressure") or 0.0)
            severity = cls._severity(
                contradiction_pressure=contradiction_pressure,
                source_count=len(dispute.get("signal_ids") or []),
                prior_unresolved_count=int(prior_unresolved.get(claim_key, 0)),
            )
            governance = ContradictionEscalationGovernance.evaluate(
                contradictions=[dispute],
                signals=[{"signal_id": signal_id} for signal_id in dispute.get("signal_ids", [])],
                prior_unresolved_count=int(prior_unresolved.get(claim_key, 0)),
                quorum_required=max(2, min(3, len(node_ids))),
            )
            reconciliation = {
                "claim_key": claim_key,
                "index": index,
                "severity": severity,
                "arbitrator_node_ids": node_ids,
                "contradiction_pressure": contradiction_pressure,
                "lifecycle_state": governance["lifecycle_state"],
                "action": governance["action"],
                "canonical_authority_granted": False,
                "lineage_preserved": True,
                "previous_dispute_hash": previous_hash,
            }
            reconciliation["dispute_hash"] = stable_hash(reconciliation)
            previous_hash = reconciliation["dispute_hash"]
            rows.append(reconciliation)
            if governance["lifecycle_state"] in {"OBSERVED", "ESCALATED", "PERSISTENT_UNRESOLVED"}:
                unresolved.append(
                    {
                        "claim_key": claim_key,
                        "persistence_state": "open",
                        "prior_unresolved_count": int(prior_unresolved.get(claim_key, 0)),
                        "next_required_action": governance["action"],
                        "dispute_hash": reconciliation["dispute_hash"],
                    }
                )

        payload = {
            "schema": "UNIGURU_DISTRIBUTED_CONTRADICTION_ARBITRATION_V1",
            "arbitrator_node_ids": node_ids,
            "contradiction_arbitration_trace": rows,
            "unresolved_contradiction_persistence": unresolved,
            "silent_merge_allowed": False,
            "replay_safe": True,
            "last_dispute_hash": previous_hash,
        }
        payload["arbitration_hash"] = stable_hash(payload)
        return payload

    @staticmethod
    def _severity(*, contradiction_pressure: float, source_count: int, prior_unresolved_count: int) -> str:
        score = _clamp((0.55 * contradiction_pressure) + (0.25 * min(source_count, 4) / 4) + (0.2 * min(prior_unresolved_count, 3) / 3))
        return _risk_band(score)


class OntologyLegitimacyBoundaryEngine:
    """Applies ontology-scoped legitimacy ceilings without mutating ontology."""

    @classmethod
    def evaluate(
        cls,
        *,
        previous_snapshot: Dict[str, Any],
        current_snapshot: Dict[str, Any],
        claims: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        drift = detect_semantic_drift(previous_snapshot, current_snapshot)
        current = {row["concept_id"]: row for row in current_snapshot.get("concepts", [])}
        boundaries: List[Dict[str, Any]] = []
        alerts: List[Dict[str, Any]] = []

        for claim in sorted(claims, key=lambda item: str(item.get("claim_key") or "")):
            concept_id = str(claim.get("concept_id") or "")
            concept = current.get(concept_id, {})
            truth_level = int(concept.get("truth_level") or 0)
            ontology_ceiling = _clamp((truth_level / 5.0) - (0.18 if drift.get("violations") else 0.0))
            uncertainty = _clamp(claim.get("uncertainty") or 0.0)
            contradiction_pressure = _clamp(claim.get("contradiction_pressure") or 0.0)
            semantic_cap = _clamp(ontology_ceiling - (0.22 * uncertainty) - (0.28 * contradiction_pressure))
            boundary = {
                "claim_key": str(claim.get("claim_key") or "unclassified_claim"),
                "concept_id": concept_id,
                "domain": concept.get("domain"),
                "truth_level": truth_level,
                "ontology_legitimacy_ceiling": ontology_ceiling,
                "semantic_legitimacy_cap": semantic_cap,
                "lineage_bound_reference": {
                    "concept_hash": stable_hash(concept) if concept else None,
                    "snapshot_version": current_snapshot.get("snapshot_version"),
                },
                "canonical_authority_granted": False,
            }
            boundary["boundary_hash"] = stable_hash(boundary)
            boundaries.append(boundary)
            if semantic_cap < _clamp(claim.get("requested_legitimacy") or 0.0) or drift.get("violations"):
                alert = {
                    "claim_key": boundary["claim_key"],
                    "alert": "CONSTITUTIONAL_ONTOLOGY_DRIFT_OR_CAP_EXCEEDED",
                    "requested_legitimacy": _clamp(claim.get("requested_legitimacy") or 0.0),
                    "semantic_legitimacy_cap": semantic_cap,
                    "ontology_drift_accepted": drift["accepted"],
                    "violation_count": len(drift.get("violations") or []),
                }
                alert["alert_hash"] = stable_hash(alert)
                alerts.append(alert)

        pressure = {
            "schema": "UNIGURU_ONTOLOGY_PRESSURE_OBSERVABILITY_V1",
            "drift": drift,
            "boundary_count": len(boundaries),
            "alert_count": len(alerts),
            "mutation_pressure_score": _clamp((len(drift.get("violations") or []) / 3.0) + (len(alerts) / max(len(boundaries), 1) * 0.35)),
        }
        pressure["pressure_hash"] = stable_hash(pressure)
        payload = {
            "schema": "UNIGURU_ONTOLOGY_LEGITIMACY_BOUNDARY_V1",
            "ontology_legitimacy_boundaries": boundaries,
            "semantic_drift_alerts": alerts,
            "ontology_pressure_observability": pressure,
            "canonical_authority_granted": False,
        }
        payload["boundary_state_hash"] = stable_hash(payload)
        return payload


class SemanticPressureObservabilityEngine:
    """Combines pressure, contradiction, ontology, and uncertainty into JSON observability."""

    @staticmethod
    def build(
        *,
        pressure_governance: Dict[str, Any],
        contradiction_arbitration: Dict[str, Any],
        ontology_boundaries: Dict[str, Any],
        uncertainty_lineage: Dict[str, Any],
    ) -> Dict[str, Any]:
        max_pressure = max(
            [float(row.get("authority_pressure_score") or 0.0) for row in pressure_governance.get("authority_pressure_logs", [])]
            or [0.0]
        )
        unresolved_count = len(contradiction_arbitration.get("unresolved_contradiction_persistence") or [])
        alert_count = len(ontology_boundaries.get("semantic_drift_alerts") or [])
        observability = {
            "schema": "UNIGURU_SEMANTIC_PRESSURE_OBSERVABILITY_V1",
            "semantic_pressure_observability": {
                "max_authority_pressure": _clamp(max_pressure),
                "unresolved_contradiction_count": unresolved_count,
                "ontology_alert_count": alert_count,
                "uncertainty_event_count": int(uncertainty_lineage.get("event_count") or 0),
                "governance_state": "ESCALATED"
                if max_pressure >= 0.55 or unresolved_count or alert_count
                else "BOUNDED_OBSERVATION",
                "canonical_authority_granted": False,
            },
            "authority_gravity_dashboard": {
                "claims": [
                    {
                        "claim_key": row.get("claim_key"),
                        "authority_pressure_score": row.get("authority_pressure_score"),
                        "risk_band": row.get("risk_band"),
                        "governance_response": row.get("governance_response"),
                    }
                    for row in pressure_governance.get("authority_pressure_logs", [])
                ],
                "dashboard_mode": "json_only",
            },
            "uncertainty_continuity_trace": uncertainty_lineage,
            "trust_lineage_observability": {
                "pressure_hash": pressure_governance.get("governance_hash"),
                "arbitration_hash": contradiction_arbitration.get("arbitration_hash"),
                "ontology_boundary_hash": ontology_boundaries.get("boundary_state_hash"),
                "uncertainty_lineage_hash": uncertainty_lineage.get("lineage_state_hash"),
            },
            "replay_safe": True,
        }
        observability["observability_hash"] = stable_hash(observability)
        return observability
