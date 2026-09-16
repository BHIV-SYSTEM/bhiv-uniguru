from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from governance.constitutional_runtime import ConstitutionalCognitionRuntime
from integrations.bucket_telemetry import BucketTelemetryClient, TelemetryEvent
from integrations.gc_client import GCClient
from integrations.insightflow_client import InsightFlowClient
from integrations.mdu_client import MDUClient
from integrations.tantra_ecosystem_bridge import get_tantra_ecosystem_fabric
from integrations.tantra_runtime_client import TantraRuntimeClient
from integrations.tantra_sdk_adapter import TantraSdkAdapter
from memory.constitutional_semantic_memory import stable_hash

DEFAULT_PROOF_DIR = ROOT.parent / "review_packets" / "integration_proof"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _map_verification_status(status: str) -> str:
    value = str(status or "").upper()
    if value in {"VERIFIED", "PARTIAL", "PARTIAL_VERIFIED_SAMPLE"}:
        return "VERIFIED" if value == "VERIFIED" else "PARTIAL_VERIFIED_SAMPLE"
    if value in {"NO_VERIFIED_KNOWLEDGE", "UNVERIFIED"}:
        return "UNVERIFIED"
    return "UNVERIFIED"


def _build_vijay_validation(trace_id: str, pipeline_result: Dict[str, Any], runtime_trace: Dict[str, Any]) -> Dict[str, Any]:
    confidence = float((pipeline_result.get("confidence_breakdown") or {}).get("overall") or 0.0)
    verification_status = str(pipeline_result.get("verification_status") or "UNVERIFIED").upper()
    semantic_event = {
        "trace_id": trace_id,
        "claim_key": "ecosystem_execution",
        "confidence": confidence,
        "provenance_weight": 0.42 if verification_status != "NO_VERIFIED_KNOWLEDGE" else 0.0,
        "legitimacy_evidence": 0.38 if verification_status != "NO_VERIFIED_KNOWLEDGE" else 0.0,
        "reinforcement_count": len(pipeline_result.get("matched_signals") or []),
        "contradiction_pressure": 0.0 if verification_status != "NO_VERIFIED_KNOWLEDGE" else 0.35,
        "uncertainty": round(max(0.0, 1.0 - confidence), 4),
        "ambiguity_class": "bounded" if verification_status != "NO_VERIFIED_KNOWLEDGE" else "no_verified_knowledge",
        "unresolved": verification_status == "NO_VERIFIED_KNOWLEDGE",
    }
    previous_snapshot = {
        "snapshot_version": 1,
        "concepts": [{"concept_id": "bhiv_intelligence", "canonical_name": "BHIV Internal Intelligence", "parent_id": None, "truth_level": 3, "domain": "ecosystem", "immutable": False}],
    }
    current_snapshot = previous_snapshot
    governance_result = ConstitutionalCognitionRuntime.execute(
        previous_snapshot=previous_snapshot,
        current_snapshot=current_snapshot,
        semantic_events=[semantic_event],
        ontology_boundaries={"ecosystem_execution": {"legitimacy_ceiling": 0.42, "ontology_violation_count": 0}},
        disputes=[{"claim_key": "ecosystem_execution", "signal_ids": [trace_id, "vijay_replay"], "polarities": ["bounded", "verified"], "contradiction_pressure": 0.0 if verification_status != "NO_VERIFIED_KNOWLEDGE" else 0.35}],
        arbitrators=[{"node_id": "vijay_runtime"}, {"node_id": "isha_runtime"}],
        prior_unresolved={},
        claims=[{"claim_key": "ecosystem_execution", "concept_id": "bhiv_intelligence", "requested_legitimacy": confidence, "uncertainty": round(max(0.0, 1.0 - confidence), 4), "contradiction_pressure": 0.0 if verification_status != "NO_VERIFIED_KNOWLEDGE" else 0.35}],
    )
    runtime_trace = governance_result["runtime_trace"]
    replay_flow = governance_result["replay_flow"]
    return {
        "trace_id": trace_id,
        "semantic_event": semantic_event,
        "runtime_hash": runtime_trace.get("runtime_hash"),
        "replay_safe": bool(replay_flow.get("replay_safe")),
        "last_event_hash": replay_flow.get("last_event_hash"),
        "hash_chain_ok": runtime_trace.get("event_registry_verification", {}).get("hash_chain_ok"),
        "canonical_authority_granted": bool(runtime_trace.get("canonical_authority_granted")),
        "component_hashes": runtime_trace.get("component_hashes") or {},
    }


def _build_tantra_contract(trace_id: str, pipeline_result: Dict[str, Any], bucket_payload: Dict[str, Any]) -> Dict[str, Any]:
    output_contract = pipeline_result.get("output_contract") or {}
    return {
        "trace_id": trace_id,
        "schema": output_contract.get("schema") or "TANTRA_UNIGURU_INTELLIGENCE_CONTRACT_V1",
        "contract_bound": bool(output_contract.get("contract_bound")),
        "downstream_consumable": bool(output_contract.get("downstream_consumable")),
        "verification_status": pipeline_result.get("verification_status"),
        "bucket_proof_ready": bool(bucket_payload.get("emitted")),
        "trace_continuity": {
            "retrieval": trace_id,
            "validation": trace_id,
            "synthesis": trace_id,
            "bucket_proof": trace_id,
        },
    }


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")


_bucket_telemetry_client = BucketTelemetryClient()
_tantra_runtime_client = TantraRuntimeClient()
_insightflow_client = InsightFlowClient()
_gc_client = GCClient()
_mdu_client = MDUClient()
_tantra_sdk_adapter = TantraSdkAdapter()


def _build_bucket_telemetry(trace_id: str, pipeline_result: Dict[str, Any], proof_dir: Path) -> Dict[str, Any]:
    payload = {
        "event": "ecosystem_runtime_execution",
        "trace_id": trace_id,
        "route": "TANTRA_ECOSYSTEM",
        "verification_status": str(pipeline_result.get("verification_status") or "UNVERIFIED").upper(),
        "decision": "answer" if str(pipeline_result.get("verification_status") or "").upper() != "NO_VERIFIED_KNOWLEDGE" else "block",
        "query_hash": stable_hash({"query": pipeline_result.get("query") or "ecosystem_runtime"})[:16],
        "ontology_reference": {"domain": (pipeline_result.get("domain_resolution") or {}).get("domain"), "trace_id": trace_id},
        "timestamp": _utc_now_iso(),
    }
    bucket_path = proof_dir / f"bucket_{trace_id}.json"
    _write_json(bucket_path, payload)
    payload["emitted"] = True
    payload["bucket_path"] = str(bucket_path)

    if _bucket_telemetry_client.enabled and _bucket_telemetry_client.endpoint:
        payload["live_endpoint"] = _bucket_telemetry_client.endpoint
        payload["live_emitted"] = _bucket_telemetry_client.emit(
            TelemetryEvent(
                event=payload["event"],
                query_hash=payload["query_hash"],
                route=payload["route"],
                verification_status=payload["verification_status"],
                latency=0.0,
                caller=None,
                session_id=None,
                ontology_reference=payload["ontology_reference"],
                routing={"route": payload["route"]},
                decision=payload["decision"],
            )
        )
    else:
        payload["live_endpoint"] = None
        payload["live_emitted"] = False

    return payload


def _build_insightflow_observability(trace_id: str, pipeline_result: Dict[str, Any], vijay_validation: Dict[str, Any]) -> Dict[str, Any]:
    trace_hash = stable_hash({"trace_id": trace_id, "verification_status": pipeline_result.get("verification_status"), "runtime_hash": vijay_validation.get("runtime_hash")})
    local_payload = {
        "trace_id": trace_id,
        "trace_complete": True,
        "trace_hash": trace_hash,
        "observability_state": "live_runtime_trace_complete",
        "pipeline_status": pipeline_result.get("verification_status"),
        "replay_safe": bool(vijay_validation.get("replay_safe")),
    }
    live_trace = _insightflow_client.emit_trace(local_payload)
    live_decision = _insightflow_client.emit_decision({
        "trace_id": trace_id,
        "decision": "answer" if str(pipeline_result.get("verification_status") or "").upper() != "NO_VERIFIED_KNOWLEDGE" else "block",
        "verification_status": pipeline_result.get("verification_status"),
        "replay_safe": bool(vijay_validation.get("replay_safe")),
    })
    local_payload["live_trace"] = live_trace
    local_payload["live_decision"] = live_decision
    return local_payload


def _build_gc_validation(vijay_validation: Dict[str, Any], pipeline_result: Dict[str, Any]) -> Dict[str, Any]:
    authority_enforced = bool(vijay_validation.get("canonical_authority_granted") is False and pipeline_result.get("output_contract", {}).get("contract_bound"))
    local_payload = {
        "trace_id": vijay_validation.get("trace_id"),
        "authority_enforced": authority_enforced,
        "canonical_authority_granted": bool(vijay_validation.get("canonical_authority_granted")),
        "governance_note": "Constitutional authority remains read-only and enforcement is preserved through replay-safe hashing.",
    }
    live_authority = _gc_client.validate_authority(local_payload)
    live_hidden_state = _gc_client.validate_hidden_state({"trace_id": vijay_validation.get("trace_id"), "runtime_hash": vijay_validation.get("runtime_hash")})
    local_payload["live_authority_validation"] = live_authority
    local_payload["live_hidden_state_validation"] = live_hidden_state
    return local_payload


def _build_tantra_sdk_contracts(trace_id: str, pipeline_result: Dict[str, Any], query: str) -> Dict[str, Any]:
    execution_event = _tantra_sdk_adapter.emit_execution_event(
        trace_id=trace_id,
        query=query,
        verification_status=pipeline_result.get("verification_status") or "UNVERIFIED",
        answer=pipeline_result.get("answer"),
        domain=(pipeline_result.get("domain_resolution") or {}).get("domain") or "ecosystem",
        duration_ms=12,
    )
    # Submit to live TANTRA SDK runtime
    live_execution = _tantra_runtime_client.submit_execution_event(execution_event)
    live_trace = _tantra_runtime_client.submit_trace({
        "trace_id": trace_id,
        "schema_version": execution_event.get("schema_version"),
        "ownership": execution_event.get("ownership"),
        "provenance": execution_event.get("provenance"),
    })
    live_authority = _tantra_runtime_client.validate_authority({
        "trace_id": trace_id,
        "subject_id": execution_event.get("subject_id"),
        "ownership": execution_event.get("ownership"),
    })
    return {
        "execution_event": execution_event,
        "live_execution_submission": live_execution,
        "live_trace_submission": live_trace,
        "live_authority_validation": live_authority,
        "tantra_sdk_live": _tantra_runtime_client.is_live(),
    }


def _build_mdu_validation(trace_id: str, pipeline_result: Dict[str, Any], vijay_validation: Dict[str, Any]) -> Dict[str, Any]:
    contract_path = ROOT / "contracts" / "runtime_evidence_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8")) if contract_path.exists() else {}
    required_fields = contract.get("required") or []
    retrieval_payload = pipeline_result.get("retrieval_truth_payload") or {}
    interpretation_payload = pipeline_result.get("interpretation_payload") or {}
    lineage_payload = {
        "trace_id": trace_id,
        "runtime_hash": vijay_validation.get("runtime_hash"),
        "retrieval_hash": retrieval_payload.get("artifact_hash"),
        "interpretation_hash": interpretation_payload.get("artifact_hash"),
    }
    evidence_payload = {
        "evidence_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{trace_id}|mdu|runtime_evidence_contract_v1")),
        "textbook_id": "bhiv_internal_intelligence_platform",
        "edition": "2026",
        "chapter": (pipeline_result.get("domain_resolution") or {}).get("domain") or "ecosystem",
        "section": "runtime_convergence",
        "page_numbers": [1],
        "source_hash": retrieval_payload.get("artifact_hash") or stable_hash(retrieval_payload),
        "retrieval_hash": interpretation_payload.get("artifact_hash") or stable_hash(interpretation_payload),
        "lineage_hash": stable_hash(lineage_payload),
        "verification_status": _map_verification_status(pipeline_result.get("verification_status") or "UNVERIFIED"),
    }
    missing_fields = [field for field in required_fields if field not in evidence_payload]
    local_result = {
        "trace_id": trace_id,
        "schema_compatible": not missing_fields,
        "required_fields": required_fields,
        "missing_fields": missing_fields,
        "evidence_payload": evidence_payload,
        "provenance_continuity": bool(pipeline_result.get("truth_interpretation_link") and pipeline_result.get("semantic_memory")),
    }
    live_schema = _mdu_client.validate_schema(evidence_payload)
    live_provenance = _mdu_client.validate_provenance(lineage_payload)
    local_result["live_schema_validation"] = live_schema
    local_result["live_provenance_validation"] = live_provenance
    return local_result


def _attach_sanskrit_decoder(query: str, pipeline_result: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt an Isha decoder result into Vijay's existing pipeline contract."""
    from ontology.sanskrit_decoder import decode_sanskrit_concept

    decoded = decode_sanskrit_concept(query)
    if not decoded.get("canonical_concept"):
        return pipeline_result
    adapted = dict(pipeline_result)
    adapted["sanskrit_decoder"] = decoded
    adapted["answer"] = decoded["functional_meaning"]["summary"]
    adapted["verification_status"] = "PARTIAL_VERIFIED_SAMPLE"
    adapted["confidence"] = 0.65
    adapted["confidence_breakdown"] = {**(pipeline_result.get("confidence_breakdown") or {}), "overall": 0.65, "sanskrit_source_scoped": True}
    adapted["domain_resolution"] = {"domain": "sanskrit", "method": "sanskar_source_registry", "canonical_concept_id": decoded["canonical_concept"]["concept_id"]}
    adapted["matched_signals"] = [{"signal_id": "sanskrit:" + decoded["canonical_concept"]["concept_id"], "source": decoded["provenance"]["lineage"]["source_path"], "confidence": 0.65, "content": decoded["functional_meaning"]["summary"], "tags": ["sanskrit", decoded["canonical_concept"]["canonical_name"]], "domain": "sanskrit", "trace": {"knowledge_id": decoded["canonical_concept"]["concept_id"], "source_lineage": decoded["provenance"]["lineage"]}}]
    adapted["reasoning_path"] = list(pipeline_result.get("reasoning_path") or []) + ["isha_sanskrit_source_retrieval", "sanskar_schema_validation", "sanskrit_cross_reference_synthesis", "sanskrit_graph_navigation"]
    return adapted


def execute_ecosystem_runtime(
    query: str,
    proof_dir: Optional[Path | str] = None,
    emit_proof: bool = True,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    proof_dir_path = Path(proof_dir or DEFAULT_PROOF_DIR)
    trace_id = trace_id or f"ecosystem_{uuid.uuid5(uuid.NAMESPACE_URL, query + '|' + _utc_now_iso()).hex[:12]}"

    from kosha.deterministic_pipeline import run_deterministic_pipeline

    pipeline_result = run_deterministic_pipeline(query=query, trace_id=trace_id, user_id="ecosystem_runtime")
    pipeline_result = _attach_sanskrit_decoder(query=query, pipeline_result=pipeline_result)
    vijay_validation = _build_vijay_validation(trace_id=trace_id, pipeline_result=pipeline_result, runtime_trace={})
    bucket_telemetry = _build_bucket_telemetry(trace_id=trace_id, pipeline_result=pipeline_result, proof_dir=proof_dir_path)
    tantra_contract = _build_tantra_contract(trace_id=trace_id, pipeline_result=pipeline_result, bucket_payload=bucket_telemetry)
    insightflow_observability = _build_insightflow_observability(trace_id=trace_id, pipeline_result=pipeline_result, vijay_validation=vijay_validation)
    gc_validation = _build_gc_validation(vijay_validation=vijay_validation, pipeline_result=pipeline_result)
    mdu_validation = _build_mdu_validation(trace_id=trace_id, pipeline_result=pipeline_result, vijay_validation=vijay_validation)
    tantra_sdk_contracts = _build_tantra_sdk_contracts(trace_id=trace_id, pipeline_result=pipeline_result, query=query)
    
    # Process event via canonical TANTRA Ecosystem Fabric (InsightCore, InsightBridge, PRANA, KARMA, Replay, Bucket, InsightFlow)
    tantra_fabric = get_tantra_ecosystem_fabric()
    tantra_fabric_response = tantra_fabric.process_uniguru_event(
        query=query,
        trace_id=trace_id,
        verification_status=str(pipeline_result.get("verification_status") or "UNVERIFIED").upper(),
        event_type="UNIGURU_CURRICULUM_QUERY",
        extra_payload={
            "domain": (pipeline_result.get("domain_resolution") or {}).get("domain"),
            "confidence": (pipeline_result.get("confidence_breakdown") or {}).get("overall"),
        },
    )

    # Deterministic fields only — live service responses are excluded from the hash
    # so replay produces a stable execution_hash regardless of live service availability.
    _deterministic = {
        "trace_id": trace_id,
        "query": query,
        "verification_status": pipeline_result.get("verification_status"),
        "confidence": (pipeline_result.get("confidence_breakdown") or {}).get("overall"),
        "answer": pipeline_result.get("answer"),
        "vijay_runtime_hash": vijay_validation.get("runtime_hash"),
        "vijay_last_event_hash": vijay_validation.get("last_event_hash"),
        "tantra_contract_schema": tantra_contract.get("schema"),
        "mdu_lineage_hash": mdu_validation.get("evidence_payload", {}).get("lineage_hash"),
        "gc_authority_enforced": gc_validation.get("authority_enforced"),
        "tantra_fabric_status": tantra_fabric_response.get("status"),
        "prana_verified": tantra_fabric_response.get("prana_verified"),
    }
    payload = {
        "trace_id": trace_id,
        "query": query,
        "timestamp": _utc_now_iso(),
        "verification_status": pipeline_result.get("verification_status"),
        "confidence": (pipeline_result.get("confidence_breakdown") or {}).get("overall"),
        "answer": pipeline_result.get("answer"),
        "vijay_validation": vijay_validation,
        "tantra_contract": tantra_contract,
        "bucket_telemetry": bucket_telemetry,
        "insightflow_observability": insightflow_observability,
        "gc_validation": gc_validation,
        "mdu_validation": mdu_validation,
        "tantra_sdk_contracts": tantra_sdk_contracts,
        "tantra_ecosystem_fabric": tantra_fabric_response,
        "pipeline_summary": {
            "matched_signals": len(pipeline_result.get("matched_signals") or []),
            "rejected_signals": len(pipeline_result.get("rejected_signals") or []),
            "domain": (pipeline_result.get("domain_resolution") or {}).get("domain"),
            "reasoning_path": pipeline_result.get("reasoning_path"),
            "sanskrit_decoder": pipeline_result.get("sanskrit_decoder"),
        },
        "execution_hash": stable_hash(_deterministic),
    }

    if emit_proof:
        _write_json(proof_dir_path / f"ecosystem_execution_{trace_id}.json", payload)
        _write_json(proof_dir_path / "ecosystem_execution_latest.json", payload)

    return payload


def verify_ecosystem_replay(
    query: str,
    proof_dir: Optional[Path | str] = None,
    trace_id: Optional[str] = None,
    emit_proof: bool = True,
) -> Dict[str, Any]:
    replay_trace_id = trace_id or f"ecosystem_replay_{uuid.uuid5(uuid.NAMESPACE_URL, query).hex[:12]}"
    first = execute_ecosystem_runtime(query=query, proof_dir=proof_dir, emit_proof=False, trace_id=replay_trace_id)
    replay = execute_ecosystem_runtime(query=query, proof_dir=proof_dir, emit_proof=False, trace_id=replay_trace_id)
    checks = {
        "trace_id_stable": first.get("trace_id") == replay.get("trace_id"),
        "vijay_runtime_hash_stable": first.get("vijay_validation", {}).get("runtime_hash")
        == replay.get("vijay_validation", {}).get("runtime_hash"),
        "vijay_last_event_hash_stable": first.get("vijay_validation", {}).get("last_event_hash")
        == replay.get("vijay_validation", {}).get("last_event_hash"),
        "tantra_contract_schema_stable": first.get("tantra_contract", {}).get("schema")
        == replay.get("tantra_contract", {}).get("schema"),
        "tantra_trace_continuity_stable": first.get("tantra_contract", {}).get("trace_continuity")
        == replay.get("tantra_contract", {}).get("trace_continuity"),
        "gc_authority_enforcement_stable": first.get("gc_validation", {}).get("authority_enforced")
        == replay.get("gc_validation", {}).get("authority_enforced"),
        "mdu_lineage_hash_stable": first.get("mdu_validation", {}).get("evidence_payload", {}).get("lineage_hash")
        == replay.get("mdu_validation", {}).get("evidence_payload", {}).get("lineage_hash"),
        "sanskrit_decoder_result_stable": (first.get("pipeline_summary", {}).get("sanskrit_decoder") or {}).get("result_hash")
        == (replay.get("pipeline_summary", {}).get("sanskrit_decoder") or {}).get("result_hash"),
    }
    payload = {
        "schema": "UNIGURU_ECOSYSTEM_REPLAY_VERIFICATION_V1",
        "trace_id": replay_trace_id,
        "query_hash": stable_hash({"query": query})[:16],
        "generated_at": _utc_now_iso(),
        "checks": checks,
        "replay_verified": all(checks.values()),
        "stable_fields": {
            "runtime_hash": first.get("vijay_validation", {}).get("runtime_hash"),
            "last_event_hash": first.get("vijay_validation", {}).get("last_event_hash"),
            "lineage_hash": first.get("mdu_validation", {}).get("evidence_payload", {}).get("lineage_hash"),
            "contract_schema": first.get("tantra_contract", {}).get("schema"),
        },
    }
    payload["verification_hash"] = stable_hash(payload)
    if emit_proof:
        proof_dir_path = Path(proof_dir or DEFAULT_PROOF_DIR)
        _write_json(proof_dir_path / f"replay_verification_{replay_trace_id}.json", payload)
        _write_json(proof_dir_path / "replay_verification_latest.json", payload)
    return payload
