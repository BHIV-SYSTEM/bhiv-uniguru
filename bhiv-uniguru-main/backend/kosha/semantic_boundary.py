from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Dict, List


def _strip_runtime_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_runtime_fields(item)
            for key, item in value.items()
            if key not in {"generated_at", "timestamp", "updated_at"}
        }
    if isinstance(value, list):
        return [_strip_runtime_fields(item) for item in value]
    return value


def _stable_hash(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(_strip_runtime_fields(payload), ensure_ascii=True, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _signal_lineage(signal: Dict[str, Any]) -> Dict[str, Any]:
    trace = signal.get("trace") if isinstance(signal.get("trace"), dict) else {}
    return {
        "signal_id": signal.get("signal_id"),
        "knowledge_id": trace.get("knowledge_id"),
        "source": signal.get("source"),
        "source_lineage": trace.get("source_lineage", {}),
        "retrieval_method": trace.get("method"),
        "trace_id": trace.get("trace_id"),
    }


def build_retrieval_truth_payload(
    *,
    trace_id: str,
    query: str,
    raw_signals: List[Dict[str, Any]],
    accepted_signals: List[Dict[str, Any]],
    rejected_signals: List[Dict[str, Any]],
    domain_resolution: Dict[str, Any],
    generated_at: str,
) -> Dict[str, Any]:
    """Immutable evidence layer. Interpretation may reference this, never edit it."""

    payload = {
        "layer": "DETERMINISTIC_RETRIEVAL_TRUTH",
        "immutable": True,
        "trace_id": trace_id,
        "query": query,
        "generated_at": generated_at,
        "domain_resolution": copy.deepcopy(domain_resolution),
        "raw_signal_count": len(raw_signals),
        "accepted_signal_ids": [signal.get("signal_id") for signal in accepted_signals],
        "rejected_signal_ids": [signal.get("signal_id") for signal in rejected_signals],
        "accepted_signals": copy.deepcopy(accepted_signals),
        "rejected_signals": copy.deepcopy(rejected_signals),
        "source_lineage": [_signal_lineage(signal) for signal in accepted_signals],
        "mutation_policy": "READ_ONLY_FOR_INTERPRETATION_LAYER",
    }
    payload["artifact_hash"] = _stable_hash(payload)
    return payload


def build_interpretation_payload(
    *,
    trace_id: str,
    synthesis: Dict[str, Any],
    confidence_breakdown: Dict[str, Any],
    consensus: Dict[str, Any],
    retrieval_truth: Dict[str, Any],
) -> Dict[str, Any]:
    """Bounded semantic interpretation linked to immutable retrieval artifacts."""

    payload = {
        "layer": "BOUNDED_SEMANTIC_INTERPRETATION",
        "trace_id": trace_id,
        "answer": synthesis.get("answer"),
        "verification_status": synthesis.get("verification_status"),
        "confidence": synthesis.get("confidence"),
        "confidence_breakdown": copy.deepcopy(confidence_breakdown),
        "contradiction_state": {
            "classification": consensus.get("ambiguity_classification"),
            "contradictions": consensus.get("contradictions", []),
            "contradiction_pressure": consensus.get("contradiction_pressure", 0.0),
        },
        "references": {
            "retrieval_truth_hash": retrieval_truth.get("artifact_hash"),
            "retrieval_trace_id": retrieval_truth.get("trace_id"),
            "accepted_signal_ids": retrieval_truth.get("accepted_signal_ids", []),
        },
        "authority_boundary": {
            "may_mutate_retrieval_truth": False,
            "may_introduce_unreferenced_claims": False,
            "free_form_output": False,
        },
    }
    payload["artifact_hash"] = _stable_hash(payload)
    return payload


def build_truth_interpretation_link(
    *,
    trace_id: str,
    retrieval_truth: Dict[str, Any],
    interpretation: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "trace_id": trace_id,
        "retrieval_truth_hash": retrieval_truth.get("artifact_hash"),
        "interpretation_hash": interpretation.get("artifact_hash"),
        "boundary_status": "ENFORCED",
        "interpretation_references_retrieval": (
            interpretation.get("references", {}).get("retrieval_truth_hash")
            == retrieval_truth.get("artifact_hash")
        ),
    }
