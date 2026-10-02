"""
Deterministic Kosha Pipeline
Clean OCR → Structured Kosha → Validated Signals → Synthesized Answer

This replaces the silent LLM fallback with explicit NO VERIFIED KNOWLEDGE responses.
Every answer is explainable. No hidden fallback.
"""
import logging
import os
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from governance.contradiction import ContradictionConsensusEngine
from governance.epistemic_confidence import EpistemicConfidenceEngine
from kosha.kosha_loader import KoshaLoader
from kosha.kosha_retriever import KoshaRetriever
from kosha.kosha_enforcer import KoshaEnforcer
from kosha.signal_validator import SignalValidator, AnswerSynthesizer, NO_KNOWLEDGE_RESPONSE
from convergence.convergence_runtime import run_convergence_pipeline
from kosha.semantic_boundary import (
    build_interpretation_payload,
    build_retrieval_truth_payload,
    build_truth_interpretation_link,
)
from memory.semantic_memory import SemanticMemoryStore
from reasoning.semantic_traversal import SemanticTraversalEngine

logger = logging.getLogger(__name__)

_KOSHA_DIR = Path(__file__).parent.parent / "data" / "kosha"
_REVIEW_LOG_DIR = Path(__file__).parent.parent.parent / "review_packets" / "proof_logs"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _new_trace_id(query: str) -> str:
    return f"trace_{uuid.uuid5(uuid.NAMESPACE_URL, query + '|' + _utc_now_iso()).hex[:16]}"


def _reasoning_for_signal(signal: Dict[str, Any]) -> Dict[str, Any]:
    validation = signal.get("_validation", {})
    return {
        "signal_id": signal.get("signal_id"),
        "why_accepted": (
            "Accepted after deterministic entity, concept, domain, contextual, "
            "tag, content, and confidence checks."
        ),
        "what_matched": {
            "tags": validation.get("matched_tags", []),
            "query_entities": validation.get("query_entities", []),
            "candidate_entities": validation.get("candidate_entities", []),
        },
        "overlap_percent": {
            "content": round(float(validation.get("content_overlap", 0.0)) * 100, 2),
            "concept": round(float(validation.get("concept_overlap", 0.0)) * 100, 2),
            "entity": round(float(validation.get("entity_overlap", 0.0)) * 100, 2),
        },
        "confidence_derivation": validation.get("confidence_derivation", {}),
    }


def _write_proof_log(trace_id: str, payload: Dict[str, Any]) -> None:
    _REVIEW_LOG_DIR.mkdir(parents=True, exist_ok=True)
    proof_path = _REVIEW_LOG_DIR / f"{trace_id}.json"
    with proof_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True, sort_keys=True)


def _bucket_contract(trace_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "event": "tantra_uniguru_intelligence_contract",
        "trace_id": trace_id,
        "trace_continuity": {
            "retrieval": trace_id,
            "validation": trace_id,
            "synthesis": trace_id,
            "contract_emission": trace_id,
            "downstream_execution": trace_id,
            "bucket_proof": trace_id,
            "immutable": True,
        },
        "accepted_signals": [signal.get("signal_id") for signal in payload.get("matched_signals", [])],
        "rejected_signals": [signal.get("signal_id") for signal in payload.get("rejected_signals", [])],
        "retrieval_truth_hash": payload.get("retrieval_truth_payload", {}).get("artifact_hash"),
        "interpretation_hash": payload.get("interpretation_payload", {}).get("artifact_hash"),
        "memory_event": payload.get("semantic_memory", {}).get("event", {}),
        "confidence_derivation": payload.get("confidence_breakdown", {}),
        "semantic_path": payload.get("semantic_path", []),
        "verification_status": payload.get("verification_status"),
        "timestamp": payload.get("generated_at"),
    }


def run_deterministic_pipeline(
    query: str,
    domain_hint: Optional[str] = None,
    trace_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Full deterministic pipeline:
    1. Load Kosha entries
    2. Validate existing entries (enforce schema)
    3. Retrieve signals via keyword+tag matching
    4. Validate signals against query (domain+tag+content)
    5. Synthesize clean answer OR return NO VERIFIED KNOWLEDGE

    No LLM fallback. No silent failure. Every decision is logged.
    """
    trace_id = trace_id or _new_trace_id(query)
    started_at = _utc_now_iso()
    user_id = user_id or "anonymous"

    # Phase 1: Load Kosha entries
    loader = KoshaLoader(data_sources=[str(_KOSHA_DIR)])
    raw_entries = loader.load_all()

    # Phase 3: Enforce Kosha schema — validate existing entries
    enforcement_result = KoshaEnforcer.validate_existing_entries(raw_entries)
    valid_entries = enforcement_result["valid_entries"]

    logger.info(
        f"Kosha enforcement: {enforcement_result['valid']}/{enforcement_result['total']} entries valid, "
        f"{enforcement_result['rejected']} rejected"
    )

    if not valid_entries:
        retrieval_truth = build_retrieval_truth_payload(
            trace_id=trace_id,
            query=query,
            raw_signals=[],
            accepted_signals=[],
            rejected_signals=[],
            domain_resolution={"domain": domain_hint or "general", "method": "no_valid_entries"},
            generated_at=started_at,
        )
        interpretation_payload = build_interpretation_payload(
            trace_id=trace_id,
            synthesis={
                "answer": NO_KNOWLEDGE_RESPONSE,
                "verification_status": "NO_VERIFIED_KNOWLEDGE",
                "confidence": 0.0,
            },
            confidence_breakdown={"overall": 0.0, "reason": "No valid Kosha entries passed schema enforcement."},
            consensus=ContradictionConsensusEngine.analyze([]),
            retrieval_truth=retrieval_truth,
        )
        truth_interpretation_link = build_truth_interpretation_link(
            trace_id=trace_id,
            retrieval_truth=retrieval_truth,
            interpretation=interpretation_payload,
        )
        memory_update = SemanticMemoryStore().update_from_pipeline(
            trace_id=trace_id,
            user_id=user_id,
            query=query,
            accepted_signals=[],
            rejected_signals=[],
            consensus=ContradictionConsensusEngine.analyze([]),
            verification_status="NO_VERIFIED_KNOWLEDGE",
            retrieval_truth_hash=retrieval_truth.get("artifact_hash"),
            interpretation_hash=interpretation_payload.get("artifact_hash"),
            truth_interpretation_link=truth_interpretation_link,
            confidence=0.0,
        )
        payload = {
            "trace_id": trace_id,
            "query": query,
            "verification_status": "NO_VERIFIED_KNOWLEDGE",
            "retrieval_truth_payload": retrieval_truth,
            "interpretation_payload": interpretation_payload,
            "truth_interpretation_link": truth_interpretation_link,
            "semantic_memory": memory_update,
            "multi_hop_traversal": SemanticTraversalEngine().traverse(query=query),
            "matched_signals": [],
            "rejected_signals": [],
            "reasoning_path": ["load_kosha", "schema_enforcement_failed", "deterministic_rejection"],
            "confidence_breakdown": {"overall": 0.0, "reason": "No valid Kosha entries passed schema enforcement."},
            "knowledge_ids_used": [],
            "domain_resolution": {"domain": domain_hint or "general", "method": "no_valid_entries"},
            "synthesis_mode": "REJECTED_NO_SYNTHESIS",
            "answer": NO_KNOWLEDGE_RESPONSE,
            "enforcement_stats": enforcement_result,
            "fallback_to_llm": False,
            "output_contract": {
                "schema": "TANTRA_UNIGURU_INTELLIGENCE_CONTRACT_V1",
                "contract_bound": True,
                "downstream_consumable": True,
                "free_form_output": False,
                "trace_id": trace_id,
            },
            "downstream_execution": {
                "consumer": "TANTRA_EXECUTION_CHAIN",
                "status": "REJECTED_NO_DOWNSTREAM_ACTION",
                "trace_id": trace_id,
            },
            "generated_at": started_at,
        }
        payload["bucket_proof"] = _bucket_contract(trace_id, payload)
        _write_proof_log(trace_id, payload)
        return payload

    # Phase 2 (retrieval): Get candidate signals from valid entries
    retriever = KoshaRetriever(valid_entries)
    raw_signals, detected_domain = retriever.retrieve(query=query, domain=domain_hint)
    for signal in raw_signals:
        signal.setdefault("trace", {})["trace_id"] = trace_id

    # Phase 4: Deterministic signal validation
    validation_result = SignalValidator.validate_all(
        signals=raw_signals,
        query=query,
    )
    consensus = ContradictionConsensusEngine.analyze(validation_result["accepted_signals"])
    for signal in validation_result["accepted_signals"]:
        validation = signal.get("_validation", {})
        source_governance = validation.get("source_governance") or signal.get("source_governance") or {}
        epistemic = EpistemicConfidenceEngine.derive(
            retrieval_confidence=float(validation.get("confidence") or signal.get("confidence") or 0.0),
            validation_details=validation,
            source_governance=source_governance,
            consensus=consensus,
        )
        validation.setdefault("confidence_derivation", {})["epistemic_confidence"] = epistemic
        validation["confidence_derivation"]["derived_confidence"] = epistemic["score"]
        signal["confidence"] = epistemic["score"]
    validation_result["accepted_signals"].sort(
        key=lambda s: float(s.get("confidence") or 0.0),
        reverse=True,
    )

    # Phase 6: deterministic synthesis from accepted signals only.
    synthesis = AnswerSynthesizer.synthesize(
        query=query,
        validation_result=validation_result,
    )

    accepted = validation_result["accepted_signals"]
    rejected = validation_result["rejected_signals"]
    domain_resolution = {}
    if raw_signals:
        domain_resolution = raw_signals[0].get("trace", {}).get("domain_resolution", {})
    domain_resolution = domain_resolution or {"domain": detected_domain or "general", "method": "retriever"}

    matched_signals = [
        {
            "signal_id": s.get("signal_id"),
            "source": s.get("source"),
            "confidence": s.get("confidence"),
            "tags": s.get("tags", []),
            "domain": s.get("domain"),
            "content": s.get("content"),
            "knowledge_id": s.get("trace", {}).get("knowledge_id"),
            "source_governance": s.get("source_governance", {}),
            "trace": s.get("trace", {}),
            "acceptance_reasoning": _reasoning_for_signal(s),
        }
        for s in accepted
    ]
    reasoning_path = [
        "query_received",
        "kosha_schema_enforced",
        "canonical_entities_extracted",
        "ontology_aware_retrieval",
        "signal_validation",
        "epistemic_confidence_derivation",
        "contradiction_consensus_analysis",
        "structured_signal_emission",
        "deterministic_synthesis" if accepted else "deterministic_rejection",
        "governance_contract_emission",
        "bucket_proof_ready",
    ]
    confidence_values = [float(s.get("confidence") or 0.0) for s in accepted]
    confidence_breakdown = {
        "overall": round(max(confidence_values), 4) if confidence_values else 0.0,
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "accepted_derivations": [
            s.get("_validation", {}).get("confidence_derivation", {}) for s in accepted
        ],
        "consensus": consensus,
    }
    semantic_path = [
        {
            "signal_id": s.get("signal_id"),
            "knowledge_id": s.get("trace", {}).get("knowledge_id"),
            "domain": s.get("domain"),
            "embedding_trace": s.get("trace", {}).get("embedding_trace", {}),
            "source_lineage": s.get("trace", {}).get("source_lineage", {}),
        }
        for s in accepted
    ]
    traversal_target = "Governance" if "governance" in query.lower() or "raj" in query.lower() else None
    multi_hop_traversal = SemanticTraversalEngine().traverse(
        query=query,
        target=traversal_target,
        max_hops=5,
    )
    retrieval_truth = build_retrieval_truth_payload(
        trace_id=trace_id,
        query=query,
        raw_signals=raw_signals,
        accepted_signals=matched_signals,
        rejected_signals=rejected,
        domain_resolution=domain_resolution,
        generated_at=started_at,
    )
    interpretation_payload = build_interpretation_payload(
        trace_id=trace_id,
        synthesis=synthesis,
        confidence_breakdown=confidence_breakdown,
        consensus=consensus,
        retrieval_truth=retrieval_truth,
    )
    truth_interpretation_link = build_truth_interpretation_link(
        trace_id=trace_id,
        retrieval_truth=retrieval_truth,
        interpretation=interpretation_payload,
    )
    semantic_memory = SemanticMemoryStore().update_from_pipeline(
        trace_id=trace_id,
        user_id=user_id,
        query=query,
        accepted_signals=accepted,
        rejected_signals=rejected,
        consensus=consensus,
        verification_status=synthesis["verification_status"],
        retrieval_truth_hash=retrieval_truth.get("artifact_hash"),
        interpretation_hash=interpretation_payload.get("artifact_hash"),
        truth_interpretation_link=truth_interpretation_link,
        confidence=float(synthesis.get("confidence") or confidence_breakdown.get("overall") or 0.0),
        ontology_lineage=semantic_path,    # Execute Knowledge Convergence Runtime
    )
    candidate_objects = [
        {
            "content": s.get("content") or s.get("clean_content") or "",
            "source": s.get("source") or s.get("knowledge_id") or "KOSHA",
            "concept": s.get("concept") or s.get("domain") or "general",
            "domain": s.get("domain"),
            "tags": s.get("tags", []),
            "confidence": s.get("confidence", 0.85),
            "authority_tier": "CANONICAL",
        }
        for s in raw_signals
    ]
    convergence_record, deduped_candidates = run_convergence_pipeline(
        query=query,
        candidates=candidate_objects,
        synthesized_answer=synthesis["answer"],
        trace_id=trace_id,
        canonical_concept_id=detected_domain or "general",
    )

    payload = {
        "trace_id": trace_id,
        "query": query,
        "answer": synthesis["answer"],
        "verification_status": synthesis["verification_status"],
        "retrieval_run_record": convergence_record.to_dict(),
        "claim_evidence_bindings": [b.to_dict() for b in convergence_record.claim_bindings],
        "selected_evidence": [e.to_dict() for e in convergence_record.selected_evidence],
        "retrieval_truth_payload": retrieval_truth,
        "interpretation_payload": interpretation_payload,
        "truth_interpretation_link": truth_interpretation_link,
        "semantic_memory": semantic_memory,
        "multi_hop_traversal": multi_hop_traversal,
        "matched_signals": matched_signals,
        "rejected_signals": rejected,
        "reasoning_path": reasoning_path,
        "semantic_path": semantic_path,
        "confidence_breakdown": confidence_breakdown,
        "consensus_analysis": consensus,
        "knowledge_ids_used": [
            s.get("trace", {}).get("knowledge_id") for s in accepted if s.get("trace", {}).get("knowledge_id")
        ],
        "domain_resolution": domain_resolution,
        "synthesis_mode": "DETERMINISTIC_FROM_ACCEPTED_SIGNALS" if accepted else "REJECTED_NO_SYNTHESIS",
        "confidence": synthesis["confidence"],
        "signals_found": len(accepted),
        "signals_rejected": len(rejected),
        "fallback_to_llm": False,
        "output_contract": {
            "schema": "TANTRA_UNIGURU_INTELLIGENCE_CONTRACT_V1",
            "contract_bound": True,
            "downstream_consumable": True,
            "free_form_output": False,
            "trace_id": trace_id,
        },
        "downstream_execution": {
            "consumer": "TANTRA_EXECUTION_CHAIN",
            "status": "READY_FOR_CONSUMPTION" if accepted else "REJECTED_NO_DOWNSTREAM_ACTION",
            "trace_id": trace_id,
        },
        "detected_domain": detected_domain,
        "reasoning": synthesis["reasoning"],
        "enforcement_stats": {
            "total_entries": enforcement_result["total"],
            "valid_entries": enforcement_result["valid"],
            "rejected_entries": enforcement_result["rejected"],
        },
        "generated_at": started_at,
    }
    payload["bucket_proof"] = _bucket_contract(trace_id, payload)
    _write_proof_log(trace_id, payload)
    return payload


def run_proof_queries(queries: List[str]) -> List[Dict[str, Any]]:
    """
    Run a batch of queries and return structured proof logs.
    Used for generating the 20-query proof log deliverable.
    """
    results = []
    for i, query in enumerate(queries):
        logger.info(f"[{i+1}/{len(queries)}] Query: {query[:60]}...")
        result = run_deterministic_pipeline(query)
        results.append({
            "query_number": i + 1,
            "trace_id": result["trace_id"],
            "query": query,
            "verification_status": result["verification_status"],
            "matched_signals": result["matched_signals"],
            "rejected_signals": result["rejected_signals"],
            "reasoning_path": result["reasoning_path"],
            "confidence_breakdown": result["confidence_breakdown"],
            "knowledge_ids_used": result["knowledge_ids_used"],
            "domain_resolution": result["domain_resolution"],
            "synthesis_mode": result["synthesis_mode"],
        })
    return results
