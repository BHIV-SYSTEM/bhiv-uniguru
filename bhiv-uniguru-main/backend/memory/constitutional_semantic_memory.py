from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVENT_LOG_PATH = ROOT / "review_packets" / "proof_logs" / "constitutional_semantic_events.jsonl"
DEFAULT_CHECKPOINT_PATH = ROOT / "review_packets" / "proof_logs" / "constitutional_semantic_checkpoint.json"
DEFAULT_OBSERVABILITY_PATH = ROOT / "review_packets" / "proof_logs" / "constitutional_semantic_observability.json"

CANONICAL_CONFIDENCE_FLOOR = 0.55


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def stable_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: stable_payload(item)
            for key, item in value.items()
            if key not in {"generated_at", "timestamp", "updated_at", "observed_at"}
        }
    if isinstance(value, list):
        return [stable_payload(item) for item in value]
    return value


def stable_hash(value: Any) -> str:
    encoded = json.dumps(stable_payload(value), ensure_ascii=True, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _load_json(path: Path, fallback: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return dict(fallback)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(fallback)


def _signal_entities(signals: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    entities: Dict[str, Dict[str, Any]] = {}
    for signal in signals:
        validation = signal.get("_validation") or {}
        for entity in validation.get("candidate_entities") or []:
            canonical = str(entity.get("canonical") or "").strip()
            if not canonical:
                continue
            entities[canonical] = {
                "canonical": canonical,
                "source_signal_id": signal.get("signal_id"),
                "source": signal.get("source"),
                "domain": signal.get("domain"),
            }
    return [entities[key] for key in sorted(entities)]


class SemanticGovernanceEngine:
    """Deterministic semantic mutation gate.

    The engine decides whether a pipeline observation may influence canonical
    memory. Interpretation can propose observations, but only this gate can
    classify them as canonical candidates or quarantine them.
    """

    @classmethod
    def evaluate(cls, request: Dict[str, Any]) -> Dict[str, Any]:
        accepted_signals = request.get("accepted_signals") or []
        rejected_signals = request.get("rejected_signals") or []
        consensus = request.get("consensus") or {}
        confidence = float(request.get("confidence") or 0.0)
        contradiction_pressure = float(consensus.get("contradiction_pressure") or 0.0)
        contradictions = consensus.get("contradictions") or []
        boundary = request.get("authority_boundary") or {}

        reasons: List[str] = []
        failure_states: List[str] = []

        if not request.get("trace_id"):
            reasons.append("missing_trace_id")
        if not request.get("retrieval_truth_hash"):
            reasons.append("missing_retrieval_truth_hash")
        if not request.get("interpretation_hash"):
            reasons.append("missing_interpretation_hash")
        if boundary.get("boundary_status") != "ENFORCED":
            reasons.append("truth_interpretation_boundary_not_enforced")
        if bool(boundary.get("interpretation_references_retrieval")) is not True:
            reasons.append("interpretation_does_not_reference_retrieval_truth")
        if request.get("verification_status") != "VERIFIED":
            reasons.append("verification_status_not_verified")
        if not accepted_signals:
            reasons.append("no_accepted_signals")
        if confidence < CANONICAL_CONFIDENCE_FLOOR:
            reasons.append("confidence_below_canonical_floor")
        if contradiction_pressure > 0 or contradictions:
            reasons.append("contradiction_requires_audit")
            failure_states.append("CONTRADICTION_INJECTION")
        if rejected_signals:
            failure_states.append("PARTIAL_REJECTION_PRESENT")

        if reasons:
            classification = "quarantined" if "contradiction_requires_audit" in reasons else "transient"
            decision = "REJECT_CANONICAL_MUTATION"
        else:
            classification = "canonical"
            decision = "ACCEPT_CANONICAL_MUTATION"

        return {
            "schema": "UNIGURU_SEMANTIC_GOVERNANCE_DECISION_V1",
            "decision": decision,
            "memory_classification": classification,
            "canonical_authority_granted": decision == "ACCEPT_CANONICAL_MUTATION",
            "reasons": reasons,
            "failure_states": failure_states,
            "confidence_floor": CANONICAL_CONFIDENCE_FLOOR,
            "contradiction_pressure": round(contradiction_pressure, 4),
            "rules": [
                "interpretation_never_mutates_retrieval_truth",
                "canonical_authority_requires_governance_acceptance",
                "contradictions_are_audit_events_not_silent_merges",
                "persistent_writes_are_append_only_and_replayable",
                "ontology_references_preserve_snapshot_lineage",
            ],
        }


class ConstitutionalSemanticMemory:
    """Append-only semantic memory event store with deterministic reconstruction."""

    def __init__(
        self,
        *,
        event_log_path: Optional[Path] = None,
        checkpoint_path: Optional[Path] = None,
        observability_path: Optional[Path] = None,
    ) -> None:
        self.event_log_path = event_log_path or DEFAULT_EVENT_LOG_PATH
        self.checkpoint_path = checkpoint_path or DEFAULT_CHECKPOINT_PATH
        self.observability_path = observability_path or DEFAULT_OBSERVABILITY_PATH

    def record_pipeline_mutation(self, request: Dict[str, Any]) -> Dict[str, Any]:
        request = dict(request)
        request.setdefault("observed_at", utc_now_iso())
        decision = SemanticGovernanceEngine.evaluate(request)
        mutation_id = self._mutation_id(request)
        existing = self._find_event(mutation_id)
        if existing:
            reconstruction = self.reconstruct()
            return self._result(
                event=existing,
                decision=existing["governance_decision"],
                reconstruction=reconstruction,
                idempotent_replay=True,
            )

        previous_hash = self._last_event_hash()
        event = {
            "schema": "UNIGURU_CONSTITUTIONAL_SEMANTIC_EVENT_V1",
            "event_type": "semantic_mutation_evaluated",
            "mutation_id": mutation_id,
            "trace_id": request.get("trace_id"),
            "user_id": request.get("user_id") or "anonymous",
            "query_hash": stable_hash({"query": request.get("query") or ""}),
            "observed_at": request["observed_at"],
            "retrieval_truth_hash": request.get("retrieval_truth_hash"),
            "interpretation_hash": request.get("interpretation_hash"),
            "accepted_signal_ids": [signal.get("signal_id") for signal in request.get("accepted_signals") or []],
            "rejected_signal_ids": [signal.get("signal_id") for signal in request.get("rejected_signals") or []],
            "entities": _signal_entities(request.get("accepted_signals") or []),
            "consensus": request.get("consensus") or {},
            "confidence": round(float(request.get("confidence") or 0.0), 4),
            "verification_status": request.get("verification_status"),
            "ontology_lineage": request.get("ontology_lineage") or [],
            "authority_boundary": request.get("authority_boundary") or {},
            "governance_decision": decision,
            "previous_event_hash": previous_hash,
        }
        event["event_hash"] = stable_hash({key: value for key, value in event.items() if key != "event_hash"})

        self._append_event(event)
        reconstruction = self.reconstruct()
        self.write_checkpoint(reconstruction)
        self.write_observability(reconstruction)
        return self._result(
            event=event,
            decision=decision,
            reconstruction=reconstruction,
            idempotent_replay=False,
        )

    def reconstruct(self, *, until_event_hash: Optional[str] = None) -> Dict[str, Any]:
        events = self.read_events()
        canonical: Dict[str, Dict[str, Any]] = {}
        transient: List[Dict[str, Any]] = []
        contradictions: List[Dict[str, Any]] = []
        lineage: List[Dict[str, Any]] = []
        hash_chain_ok = True
        previous_hash: Optional[str] = None

        for event in events:
            expected = stable_hash({key: value for key, value in event.items() if key != "event_hash"})
            if event.get("event_hash") != expected or event.get("previous_event_hash") != previous_hash:
                hash_chain_ok = False

            decision = event.get("governance_decision") or {}
            classification = decision.get("memory_classification")
            if classification == "canonical":
                for entity in event.get("entities") or []:
                    canonical_name = entity["canonical"]
                    current = canonical.setdefault(
                        canonical_name,
                        {
                            "canonical": canonical_name,
                            "lineage_event_hashes": [],
                            "trace_ids": [],
                            "source_signal_ids": [],
                            "confidence": 0.0,
                        },
                    )
                    current["lineage_event_hashes"].append(event["event_hash"])
                    current["trace_ids"].append(event["trace_id"])
                    if entity.get("source_signal_id"):
                        current["source_signal_ids"].append(entity["source_signal_id"])
                    current["confidence"] = max(float(current["confidence"]), float(event.get("confidence") or 0.0))
            else:
                transient.append(
                    {
                        "event_hash": event.get("event_hash"),
                        "trace_id": event.get("trace_id"),
                        "classification": classification,
                        "reasons": decision.get("reasons") or [],
                    }
                )

            if event.get("consensus", {}).get("contradictions"):
                contradictions.append(
                    {
                        "event_hash": event.get("event_hash"),
                        "trace_id": event.get("trace_id"),
                        "contradictions": event.get("consensus", {}).get("contradictions"),
                        "pressure": event.get("consensus", {}).get("contradiction_pressure"),
                    }
                )
            lineage.append(
                {
                    "event_hash": event.get("event_hash"),
                    "previous_event_hash": event.get("previous_event_hash"),
                    "trace_id": event.get("trace_id"),
                    "classification": classification,
                    "retrieval_truth_hash": event.get("retrieval_truth_hash"),
                    "interpretation_hash": event.get("interpretation_hash"),
                }
            )
            previous_hash = event.get("event_hash")
            if until_event_hash and previous_hash == until_event_hash:
                break

        payload = {
            "schema": "UNIGURU_CONSTITUTIONAL_SEMANTIC_RECONSTRUCTION_V1",
            "event_count": len(lineage),
            "canonical_memory": {key: canonical[key] for key in sorted(canonical)},
            "transient_memory": transient,
            "contradiction_audit": contradictions,
            "lineage": lineage,
            "replay_integrity": {
                "hash_chain_ok": hash_chain_ok,
                "last_event_hash": previous_hash,
                "rollback_target": until_event_hash,
            },
        }
        payload["state_hash"] = stable_hash(payload)
        return payload

    def rollback_preview(self, event_hash: str) -> Dict[str, Any]:
        return self.reconstruct(until_event_hash=event_hash)

    def read_events(self) -> List[Dict[str, Any]]:
        if not self.event_log_path.exists():
            return []
        events: List[Dict[str, Any]] = []
        for line in self.event_log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            events.append(json.loads(line))
        return events

    def write_checkpoint(self, reconstruction: Dict[str, Any]) -> None:
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path.write_text(
            json.dumps(reconstruction, indent=2, ensure_ascii=True, sort_keys=True),
            encoding="utf-8",
        )

    def write_observability(self, reconstruction: Dict[str, Any]) -> Dict[str, Any]:
        telemetry = {
            "schema": "UNIGURU_CONSTITUTIONAL_SEMANTIC_OBSERVABILITY_V1",
            "generated_at": utc_now_iso(),
            "event_count": reconstruction["event_count"],
            "canonical_entity_count": len(reconstruction["canonical_memory"]),
            "transient_event_count": len(reconstruction["transient_memory"]),
            "contradiction_event_count": len(reconstruction["contradiction_audit"]),
            "hash_chain_ok": reconstruction["replay_integrity"]["hash_chain_ok"],
            "last_event_hash": reconstruction["replay_integrity"]["last_event_hash"],
            "state_hash": reconstruction["state_hash"],
        }
        self.observability_path.parent.mkdir(parents=True, exist_ok=True)
        self.observability_path.write_text(
            json.dumps(telemetry, indent=2, ensure_ascii=True, sort_keys=True),
            encoding="utf-8",
        )
        return telemetry

    def _result(
        self,
        *,
        event: Dict[str, Any],
        decision: Dict[str, Any],
        reconstruction: Dict[str, Any],
        idempotent_replay: bool,
    ) -> Dict[str, Any]:
        return {
            "schema": "UNIGURU_CONSTITUTIONAL_SEMANTIC_MEMORY_RESULT_V1",
            "observable": True,
            "replayable": True,
            "lineage_traceable": True,
            "rollback_safe": True,
            "event_log_path": str(self.event_log_path.as_posix()),
            "checkpoint_path": str(self.checkpoint_path.as_posix()),
            "observability_path": str(self.observability_path.as_posix()),
            "mutation_id": event["mutation_id"],
            "event_hash": event["event_hash"],
            "idempotent_replay": idempotent_replay,
            "governance_decision": decision,
            "canonical_authority_granted": decision["canonical_authority_granted"],
            "canonical_memory_keys": sorted(reconstruction["canonical_memory"]),
            "transient_event_count": len(reconstruction["transient_memory"]),
            "contradiction_event_count": len(reconstruction["contradiction_audit"]),
            "state_hash": reconstruction["state_hash"],
            "replay_integrity": reconstruction["replay_integrity"],
            "event": {
                "event_type": event["event_type"],
                "trace_id": event["trace_id"],
                "entities_touched": [entity["canonical"] for entity in event.get("entities") or []],
                "memory_classification": decision["memory_classification"],
                "canonical_authority_granted": decision["canonical_authority_granted"],
                "contradiction_pressure": decision["contradiction_pressure"],
                "updated_at": event["observed_at"],
            },
        }

    def _mutation_id(self, request: Dict[str, Any]) -> str:
        return stable_hash(
            {
                "trace_id": request.get("trace_id"),
                "user_id": request.get("user_id") or "anonymous",
                "retrieval_truth_hash": request.get("retrieval_truth_hash"),
                "interpretation_hash": request.get("interpretation_hash"),
                "accepted_signal_ids": [signal.get("signal_id") for signal in request.get("accepted_signals") or []],
                "rejected_signal_ids": [signal.get("signal_id") for signal in request.get("rejected_signals") or []],
                "verification_status": request.get("verification_status"),
            }
        )

    def _append_event(self, event: Dict[str, Any]) -> None:
        self.event_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.event_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=True, sort_keys=True) + "\n")

    def _last_event_hash(self) -> Optional[str]:
        events = self.read_events()
        if not events:
            return None
        return events[-1].get("event_hash")

    def _find_event(self, mutation_id: str) -> Optional[Dict[str, Any]]:
        for event in self.read_events():
            if event.get("mutation_id") == mutation_id:
                return event
        return None


def build_pipeline_memory_request(
    *,
    trace_id: str,
    user_id: str,
    query: str,
    accepted_signals: List[Dict[str, Any]],
    rejected_signals: List[Dict[str, Any]],
    consensus: Dict[str, Any],
    verification_status: str,
    retrieval_truth_hash: Optional[str],
    interpretation_hash: Optional[str],
    truth_interpretation_link: Optional[Dict[str, Any]],
    confidence: float,
    ontology_lineage: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return {
        "trace_id": trace_id,
        "user_id": user_id,
        "query": query,
        "accepted_signals": accepted_signals,
        "rejected_signals": rejected_signals,
        "consensus": consensus,
        "verification_status": verification_status,
        "retrieval_truth_hash": retrieval_truth_hash,
        "interpretation_hash": interpretation_hash,
        "authority_boundary": truth_interpretation_link or {},
        "confidence": confidence,
        "ontology_lineage": ontology_lineage or [],
    }
