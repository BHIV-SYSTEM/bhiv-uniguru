from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
MASTERDB = ROOT / "masterdb" / "balbharti" / "sample_ingestion_dataset.json"
PROOF_DIR = ROOT / "review_packets" / "proof_logs"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from governance.constitutional_runtime import ConstitutionalCognitionRuntime
from learning_runtime.learning_intelligence import build_learning_intelligence
from memory.constitutional_semantic_memory import stable_hash, utc_now_iso
from ontology.sanskrit_decoder import decode_sanskrit_concept, load_sanskar_registry, traverse_concept_graph
from retrieval.retrieval_engine import retrieve_from_masterdb
from service.ecosystem_runtime import execute_ecosystem_runtime, verify_ecosystem_replay


SCHEMA_VERSION = "UNIGURU_RUNTIME_RESPONSE_CONTRACT_V1"


class RuntimeRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    grade: Optional[int] = Field(default=None, ge=1, le=10)
    medium: Optional[str] = None
    subject: Optional[str] = None
    emit_proof: bool = True


class SanskritDecoderRequest(BaseModel):
    query: Optional[str] = Field(default=None, max_length=2000)
    concept_id: Optional[str] = Field(default=None, max_length=200)
    emit_proof: bool = True
    trace_id: Optional[str] = None

    @field_validator("query")
    @classmethod
    def _normalize_query(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            normalized = value.strip()
            if not normalized:
                raise ValueError("query must not be empty or whitespace-only.")
            return normalized
        return value

    @field_validator("concept_id")
    @classmethod
    def _normalize_concept_id(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            normalized = value.strip()
            if not normalized:
                raise ValueError("concept_id must not be empty or whitespace-only.")
            return normalized
        return value

    @model_validator(mode="after")
    def _check_at_least_one(self) -> "SanskritDecoderRequest":
        if not self.query and not self.concept_id:
            raise ValueError("Either query or concept_id must be provided.")
        return self


app = FastAPI(
    title="UniGuru Unified Constitutional Runtime",
    version="1.0.0",
    description="Canonical query-to-governance runtime contract for UniGuru.",
)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9]+", str(text or "").lower()))


def _load_masterdb() -> List[Dict[str, Any]]:
    if not MASTERDB.exists():
        return []
    loaded = json.loads(MASTERDB.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, list) else []


def _retrieve(query: str, request: RuntimeRequest) -> Dict[str, Any]:
    return retrieve_from_masterdb(
        query=query,
        grade=request.grade,
        medium=request.medium,
        subject=request.subject,
    )


def _interpret(query: str, retrieval: Dict[str, Any]) -> Dict[str, Any]:
    record = retrieval.get("best_record") or {}
    if not record:
        interpretation = {
            "claim_key": "unmatched_curriculum_query",
            "concept_id": "masterdb_unmatched",
            "summary": "No governed MasterDB curriculum record matched the query.",
            "answer": "I do not have a verified Balbharti curriculum record for this query yet.",
            "uncertainty": 0.78,
            "verification_status": "UNVERIFIED",
        }
    else:
        examples = record.get("examples") or []
        questions = record.get("questions") or []
        related_concepts = [related.get("concept") for related in retrieval.get("related_records", []) if related.get("concept")]
        answer_parts = [
            f"{record.get('concept')}: {record.get('definition')}",
            f"Example: {examples[0]}" if examples else "",
            f"Practice: {questions[0]}" if questions else "",
        ]
        interpretation = {
            "claim_key": str(record.get("concept") or "curriculum_concept").lower().replace(" ", "_"),
            "concept_id": str(record.get("record_id")),
            "summary": f"{record.get('medium')} Grade {record.get('grade')} {record.get('subject')} concept.",
            "answer": " ".join(part for part in answer_parts if part),
            "related_concepts": related_concepts,
            "uncertainty": round(1.0 - float(retrieval.get("confidence") or 0.0), 4),
            "verification_status": "PARTIAL_VERIFIED_SAMPLE"
            if (record.get("source_lineage") or {}).get("provenance_status") == "sample_seed"
            else "VERIFIED",
        }
    interpretation["interpretation_hash"] = stable_hash(interpretation)
    return interpretation


def _govern(query: str, retrieval: Dict[str, Any], interpretation: Dict[str, Any]) -> Dict[str, Any]:
    confidence = float(retrieval.get("confidence") or 0.0)
    contradiction_pressure = 0.0 if retrieval.get("best_record") else 0.35
    semantic_event = {
        "trace_id": stable_hash({"query": query})[:16],
        "claim_key": interpretation["claim_key"],
        "confidence": confidence,
        "provenance_weight": 0.42 if retrieval.get("best_record") else 0.0,
        "legitimacy_evidence": 0.34 if retrieval.get("best_record") else 0.0,
        "reinforcement_count": len(retrieval.get("matches") or []),
        "contradiction_pressure": contradiction_pressure,
        "uncertainty": interpretation["uncertainty"],
        "ambiguity_class": "sample_seed_requires_review"
        if interpretation["verification_status"] == "PARTIAL_VERIFIED_SAMPLE"
        else "unmatched_or_unverified",
        "unresolved": interpretation["verification_status"] != "VERIFIED",
    }
    previous_snapshot = {
        "snapshot_version": 1,
        "concepts": [
            {
                "concept_id": "masterdb_curriculum",
                "canonical_name": "MasterDB Curriculum",
                "parent_id": None,
                "truth_level": 3,
                "domain": "curriculum",
                "immutable": False,
            }
        ],
    }
    current_snapshot = previous_snapshot
    ontology_boundaries = {
        interpretation["claim_key"]: {"legitimacy_ceiling": 0.42, "ontology_violation_count": 0},
        "default": {"legitimacy_ceiling": 0.32, "ontology_violation_count": 0},
    }
    disputes = []
    if contradiction_pressure:
        disputes.append(
            {
                "claim_key": interpretation["claim_key"],
                "signal_ids": ["masterdb_lookup", "runtime_boundary"],
                "polarities": ["unmatched", "requires_verified_curriculum"],
                "contradiction_pressure": contradiction_pressure,
            }
        )
    runtime = ConstitutionalCognitionRuntime.execute(
        previous_snapshot=previous_snapshot,
        current_snapshot=current_snapshot,
        semantic_events=[semantic_event],
        ontology_boundaries=ontology_boundaries,
        disputes=disputes,
        arbitrators=[{"node_id": "isha_runtime"}, {"node_id": "vijay_replay"}],
        prior_unresolved={},
        claims=[
            {
                "claim_key": interpretation["claim_key"],
                "concept_id": "masterdb_curriculum",
                "requested_legitimacy": confidence,
                "uncertainty": interpretation["uncertainty"],
                "contradiction_pressure": contradiction_pressure,
            }
        ],
    )
    return {"semantic_event": semantic_event, "runtime": runtime}


def _build_learning_state(query: str, retrieval: Dict[str, Any], interpretation: Dict[str, Any]) -> Dict[str, Any]:
    return build_learning_intelligence(query, retrieval)


def execute_runtime(request: RuntimeRequest) -> Dict[str, Any]:
    query = request.query.strip()
    retrieval = _retrieve(query, request)
    interpretation = _interpret(query, retrieval)
    learning_state = _build_learning_state(query, retrieval, interpretation)
    governed = _govern(query, retrieval, interpretation)
    runtime_trace = governed["runtime"]["runtime_trace"]
    components = governed["runtime"]["components"]
    observability = components["observability"]["semantic_pressure_observability"]
    trust_rows = components["trust_propagation"]["authority_pressure_logs"]
    contradiction = components["contradiction_escalation"]
    ontology = components["ontology_lineage"]

    trace_id = governed["semantic_event"]["trace_id"]
    payload = {
        "response_payload": {
            "answer": interpretation["answer"],
            "matched_record": retrieval.get("best_record"),
            "retrieval_confidence": retrieval["confidence"],
            "source_lineage": (retrieval.get("best_record") or {}).get("source_lineage"),
            "curriculum_mapping": {
                "matched_record_id": (retrieval.get("best_record") or {}).get("record_id"),
                "curriculum_version": (retrieval.get("best_record") or {}).get("curriculum_version"),
                "version": (retrieval.get("best_record") or {}).get("version"),
                "provenance_status": ((retrieval.get("best_record") or {}).get("source_lineage") or {}).get("provenance_status"),
                "chapter_recommendations": retrieval.get("chapter_recommendations"),
                "learning_objectives": retrieval.get("learning_objectives"),
            },
            "learning_state": learning_state,
        },
        "trust_state": {
            "trust_score": trust_rows[0]["trust_ceiling"] if trust_rows else 0.0,
            "authority_pressure_score": trust_rows[0]["authority_pressure_score"] if trust_rows else 0.0,
            "governance_response": trust_rows[0]["governance_response"] if trust_rows else "NO_TRUST_SIGNAL",
        },
        "uncertainty_state": {
            "score": interpretation["uncertainty"],
            "classification": governed["semantic_event"]["ambiguity_class"],
            "preserved": True,
        },
        "contradiction_state": {
            "unresolved_count": len(contradiction.get("unresolved_contradiction_persistence") or []),
            "silent_merge_allowed": contradiction.get("silent_merge_allowed"),
            "arbitration_hash": contradiction.get("arbitration_hash"),
        },
        "ontology_boundary_state": {
            "alert_count": len(ontology.get("semantic_drift_alerts") or []),
            "boundary_state_hash": ontology.get("boundary_state_hash"),
            "canonical_authority_granted": False,
        },
        "constitutional_reasoning_summary": {
            "flow": [
                "query",
                "masterdb_lookup",
                "semantic_interpretation",
                "constitutional_evaluation",
                "trust_contradiction_ontology_evaluation",
                "bounded_response_generation",
                "explanation_layer",
                "replay_artifact_emission",
            ],
            "verification_status": interpretation["verification_status"],
            "observability_state": observability.get("governance_state"),
            "canonical_authority_granted": False,
        },
        "trace_id": trace_id,
        "runtime_hash": runtime_trace["runtime_hash"],
        "schema_version": SCHEMA_VERSION,
    }
    payload["contract_hash"] = stable_hash(payload)
    if request.emit_proof:
        PROOF_DIR.mkdir(parents=True, exist_ok=True)
        proof_path = PROOF_DIR / f"uniguru_runtime_execution_{trace_id}.json"
        proof_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")
        latest_path = PROOF_DIR / "uniguru_runtime_execution_latest.json"
        latest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    return payload


@app.post("/runtime/execute")
def runtime_execute(request: RuntimeRequest) -> Dict[str, Any]:
    return execute_runtime(request)


@app.post("/runtime/sanskrit/decode")
@app.post("/v2/runtime/sanskrit/decode")
def runtime_sanskrit_decode(request: SanskritDecoderRequest) -> Dict[str, Any]:
    target = request.query or request.concept_id
    if not target:
        raise HTTPException(status_code=400, detail="Either 'query' or 'concept_id' must be provided.")
    decoder_result = decode_sanskrit_concept(target)
    trace_id = f"sanskrit_{stable_hash({'result': decoder_result['result_hash']})[:16]}"

    # Attach Vagdhenu chanting analysis & audio if available
    audio_info = None
    try:
        from sanskrit.vagdhenu.service import get_vagdhenu_service
        vagdhenu = get_vagdhenu_service()
        chant_resp = vagdhenu.generate_chant(target)
        if chant_resp.available:
            audio_info = chant_resp.model_dump()
    except Exception as exc:
        audio_info = {"available": False, "reason": str(exc)}

    payload = {
        "trace_id": trace_id,
        "decoder_result": decoder_result,
        "governed_response": decoder_result["governed_response"],
        "audio": audio_info,
        "replay": {
            "replay_key": decoder_result["result_hash"],
            "replay_safe": True,
            "input_trace_id_accepted": request.trace_id is None or request.trace_id == trace_id,
        },
        "schema_version": "UNIGURU_SANSKRIT_DECODER_RESPONSE_V1",
    }
    payload["response_hash"] = stable_hash(payload)
    if request.emit_proof:
        PROOF_DIR.mkdir(parents=True, exist_ok=True)
        proof_path = PROOF_DIR / f"sanskrit_decoder_{trace_id}.json"
        proof_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    return payload


class ChantRuntimeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    meter: Optional[str] = None
    reference_audio: Optional[str] = None


@app.post("/runtime/sanskrit/chant")
@app.post("/v2/runtime/sanskrit/chant")
def runtime_sanskrit_chant(request: ChantRuntimeRequest) -> Dict[str, Any]:
    from sanskrit.vagdhenu.service import get_vagdhenu_service
    service = get_vagdhenu_service()
    resp = service.generate_chant(
        sanskrit_text=request.text,
        meter=request.meter,
        reference_audio=request.reference_audio,
    )
    return resp.model_dump()


@app.get("/runtime/audio/{audio_id}")
@app.get("/v2/runtime/audio/{audio_id}")
def runtime_stream_audio(audio_id: str):
    from sanskrit.vagdhenu.storage import AudioStorage
    from fastapi.responses import Response
    storage = AudioStorage()
    result = storage.get_bytes(audio_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Audio not found: {audio_id}")
    audio_bytes, meta = result
    media_type = "audio/wav" if meta.file_format == "wav" else f"audio/{meta.file_format}"
    return Response(
        content=audio_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f"inline; filename={audio_id}.{meta.file_format}",
            "Accept-Ranges": "bytes",
        },
    )


class GraphTraverseRequest(BaseModel):
    """Request model for the multi-hop Knowledge Graph traversal endpoint."""
    start: str = Field(..., min_length=1, max_length=200, description="Starting Sanskrit concept (IAST, Devanagari, or canonical name).")
    edge_types: Optional[List[str]] = Field(
        default=None,
        description=(
            "Edge types to follow. Leave null/empty for all edges. "
            "Allowed values: canonical_cross_reference, related_deity, related_loka, "
            "related_kosha, related_chakra, related_yantra, related_vidya, "
            "referenced_in_shastra, retrieved_evidence."
        ),
    )
    max_depth: int = Field(default=3, ge=1, le=6, description="Maximum hop depth (1–6).")
    emit_proof: bool = True

    @field_validator("start")
    @classmethod
    def _normalize_start(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("start must not be empty or whitespace-only.")
        return normalized


@app.post("/v2/runtime/sanskrit/graph/traverse")
def graph_traverse(request: GraphTraverseRequest) -> Dict[str, Any]:
    """Multi-hop civilizational knowledge graph traversal.

    Walks the Sanskrit Civilizational Knowledge Graph outward from the start concept,
    following edges of the specified types up to max_depth hops. Returns an ordered
    path of hop frames and the full visited sub-graph with provenance on every edge.
    """
    registry, metadata_by_id = load_sanskar_registry()
    result = traverse_concept_graph(
        start=request.start,
        edge_types=request.edge_types,
        max_depth=request.max_depth,
        registry=registry,
        metadata_by_id=metadata_by_id,
    )
    trace_id = f"graph_traverse_{stable_hash({'start': request.start, 'depth': request.max_depth})[:16]}"
    payload = {
        "trace_id": trace_id,
        "traversal_result": result,
        "schema_version": "UNIGURU_GRAPH_TRAVERSAL_RESPONSE_V1",
        "replay_safe": result.get("traversal_metadata", {}).get("replay_safe", True),
    }
    payload["response_hash"] = stable_hash(payload)
    if request.emit_proof:
        PROOF_DIR.mkdir(parents=True, exist_ok=True)
        proof_path = PROOF_DIR / f"graph_traverse_{trace_id}.json"
        proof_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    return payload


class EcosystemRuntimeRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    emit_proof: bool = True
    trace_id: Optional[str] = None

    @field_validator("query")
    @classmethod
    def _normalize_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query must not be empty or whitespace-only.")
        return normalized


@app.post("/runtime/ecosystem/execute")
def ecosystem_runtime_execute(request: EcosystemRuntimeRequest) -> Dict[str, Any]:
    return execute_ecosystem_runtime(
        query=request.query,
        emit_proof=request.emit_proof,
        trace_id=request.trace_id,
    )


@app.post("/runtime/ecosystem/replay")
def ecosystem_runtime_replay(request: EcosystemRuntimeRequest) -> Dict[str, Any]:
    return verify_ecosystem_replay(
        query=request.query,
        emit_proof=request.emit_proof,
        trace_id=request.trace_id,
    )


@app.post("/mitra/ecosystem/ask")
def mitra_ecosystem_ask(request: EcosystemRuntimeRequest) -> Dict[str, Any]:
    result = execute_ecosystem_runtime(
        query=request.query,
        emit_proof=request.emit_proof,
        trace_id=request.trace_id,
    )
    return {
        "trace_id": result.get("trace_id"),
        "answer": result.get("answer"),
        "verification_status": result.get("verification_status"),
        "confidence": result.get("confidence"),
        "decision": result.get("bucket_telemetry", {}).get("decision"),
        "replay_safe": result.get("vijay_validation", {}).get("replay_safe"),
        "contract_schema": result.get("tantra_contract", {}).get("schema"),
        "downstream_consumable": result.get("tantra_contract", {}).get("downstream_consumable"),
        "observability_state": result.get("insightflow_observability", {}).get("observability_state"),
        "evidence": {
            "ecosystem_proof": "review_packets/integration_proof/ecosystem_execution_latest.json",
            "bucket_proof": result.get("bucket_telemetry", {}).get("bucket_path"),
        },
    }


@app.get("/v2/convergence/authority_map")
def get_convergence_authority_map() -> Dict[str, Any]:
    from convergence.authority_contract import get_authority_map
    return get_authority_map().to_dict()


class EvidenceValidationRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    synthesized_answer: str = Field(..., min_length=1, max_length=5000)
    candidates: List[Dict[str, Any]] = Field(default_factory=list)


@app.post("/v2/convergence/validate_evidence")
def validate_convergence_evidence(req: EvidenceValidationRequest) -> Dict[str, Any]:
    from convergence.convergence_runtime import run_convergence_pipeline
    record, deduped = run_convergence_pipeline(
        query=req.query,
        candidates=req.candidates,
        synthesized_answer=req.synthesized_answer,
    )
    return {
        "retrieval_run_record": record.to_dict(),
        "deduplicated_candidates": deduped,
        "valid": record.verification_status != "NO_VERIFIED_KNOWLEDGE",
    }


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "uniguru-ecosystem-runtime",
        "schema_version": SCHEMA_VERSION,
        "capabilities": [
            "runtime_execute",
            "ecosystem_execute",
            "ecosystem_replay",
            "mitra_governed_ask",
            "sanskrit_decoder",
            "knowledge_convergence",
        ],
    }


@app.get("/ready")
def ready() -> Dict[str, Any]:
    return {
        "status": "ready",
        "proof_dir": str(PROOF_DIR),
        "masterdb_present": MASTERDB.exists(),
    }


@app.get("/metrics")
def metrics() -> str:
    return "\n".join(
        [
            "# HELP uniguru_ecosystem_runtime_info Ecosystem runtime capability metadata",
            "# TYPE uniguru_ecosystem_runtime_info gauge",
            'uniguru_ecosystem_runtime_info{service="uniguru",capability="bhiv_ecosystem"} 1',
            "# HELP uniguru_ecosystem_runtime_ready Runtime readiness flag",
            "# TYPE uniguru_ecosystem_runtime_ready gauge",
            "uniguru_ecosystem_runtime_ready 1",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the UniGuru unified constitutional runtime.")
    parser.add_argument("query", nargs="?", default="What is a balanced diet in Class 6 Science?")
    parser.add_argument("--grade", type=int, default=None)
    parser.add_argument("--medium", default=None)
    parser.add_argument("--subject", default=None)
    parser.add_argument("--no-proof", action="store_true")
    args = parser.parse_args()
    payload = execute_runtime(
        RuntimeRequest(
            query=args.query,
            grade=args.grade,
            medium=args.medium,
            subject=args.subject,
            emit_proof=not args.no_proof,
        )
    )
    print(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
