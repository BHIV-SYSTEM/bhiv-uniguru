"""
Production Runtime Convergence — Phase 6

Implements and validates the canonical execution path:

  Student Query
  → Retrieval (MasterDB)
  → Curriculum Intelligence (lineage + concept extraction)
  → Learning Intelligence (gap detection + path generation)
  → Mastery Intelligence (mastery engine)
  → Constitutional Runtime (rule engine)
  → Runtime Contract (enforcement)

No parallel execution paths.
"""

from __future__ import annotations

import json
import hashlib
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
_RETRIEVAL_DIR = ROOT / "retrieval"
_RETRIEVAL_ENGINE = ROOT / "retrieval" / "retrieval_engine.py"
_CANONICAL_MANIFEST = ROOT / "canonical_dataset_manifest.json"
_KNOWLEDGE_PACK_MANIFEST = ROOT / "production_knowledge_pack" / "manifest.json"
_CONSTITUTION_METADATA = ROOT / "production_knowledge_pack" / "constitution_metadata.json"
_RUNTIME_SCHEMA_VERSION = "UNIGURU_CANONICAL_RUNTIME_V2"
_REQUIRED_PIPELINE_STAGES = [
    "StudentQuery",
    "Retrieval",
    "CurriculumIntelligence",
    "LearningIntelligence",
    "MasteryIntelligence",
    "ConstitutionalRuntime",
    "RuntimeContract",
]

# Ensure both project root and the retrieval package dir are on sys.path
for _p in [str(ROOT), str(ROOT / "backend"), str(_RETRIEVAL_DIR.parent)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ---------------------------------------------------------------------------
# Internal imports — canonical path only, no parallel retrieval
# ---------------------------------------------------------------------------
# Load retrieval_engine via importlib to handle root-level retrieval package
import importlib.util as _ilu

def _load_retrieval_engine():
    spec = _ilu.spec_from_file_location("_retrieval_engine", str(_RETRIEVAL_ENGINE))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_re_mod = _load_retrieval_engine()
retrieve_from_masterdb = _re_mod.retrieve_from_masterdb

try:
    from learning_runtime.learning_intelligence import build_learning_intelligence
except ModuleNotFoundError:
    from .learning_intelligence import build_learning_intelligence  # type: ignore

try:
    from learning_runtime.mastery_engine import MasteryEngine, compute_concept_mastery
except ModuleNotFoundError:
    from .mastery_engine import MasteryEngine, compute_concept_mastery  # type: ignore


# ---------------------------------------------------------------------------
# Canonical Runtime Orchestrator
# ---------------------------------------------------------------------------


class CanonicalRuntime:
    """
    Single, authoritative execution path for all student queries.

    Every query flows through exactly this sequence:
        1. Retrieval
        2. Curriculum Intelligence
        3. Learning Intelligence
        4. Mastery Intelligence
        5. Constitutional Runtime (optional — only if backend.core available)
        6. Runtime Contract binding
    """

    def __init__(self):
        self._mastery_engines: Dict[str, MasteryEngine] = {}

        # Optional constitutional rule engine
        self._rule_engine = None
        try:
            from backend.core.engine import RuleEngine
            self._rule_engine = RuleEngine()
        except Exception:
            pass  # Operate without constitutional layer in standalone mode

    def _get_or_create_engine(self, student_id: str, grade: int = 1) -> MasteryEngine:
        if student_id not in self._mastery_engines:
            self._mastery_engines[student_id] = MasteryEngine(student_id=student_id, grade=grade)
        return self._mastery_engines[student_id]

    def _load_json_file(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise ValueError(f"[SAFETY_GATE] Missing required production artifact: {path.relative_to(ROOT)}")
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"[SAFETY_GATE] Invalid production artifact shape: {path.relative_to(ROOT)}")
        return loaded

    def _canonical_manifest(self) -> Dict[str, Any]:
        return self._load_json_file(_CANONICAL_MANIFEST)

    def _knowledge_pack_manifest(self) -> Dict[str, Any]:
        return self._load_json_file(_KNOWLEDGE_PACK_MANIFEST)

    def _constitution_metadata(self) -> Dict[str, Any]:
        return self._load_json_file(_CONSTITUTION_METADATA)

    def _expected_lineage_hash(self, evidence: Dict[str, Any]) -> str:
        lineage_str = (
            f"{evidence.get('textbook_id')}::{evidence.get('edition')}::"
            f"{evidence.get('chapter')}::{evidence.get('section')}::{evidence.get('page_numbers')}"
        )
        return hashlib.sha256(lineage_str.encode("utf-8")).hexdigest()

    def _blocked_contract(self, request_id: str, student_id: str, query: str, reason: str) -> Dict[str, Any]:
        return {
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "schema_version": _RUNTIME_SCHEMA_VERSION,
            "student_id": student_id,
            "query": query,
            "blocked": True,
            "block_reason": reason,
            "verification_status": "BLOCKED",
            "convergence_validated": False,
        }

    def _validate_production_gates(self, best_record: Dict[str, Any], evidence: Dict[str, Any]) -> None:
        """
        Strict production safety gates — raises ValueError immediately on failure.
        No silent fallback is permitted.
        """
        # Gate 1: Authority — record must be from canonical path
        manifest = self._canonical_manifest()
        pack_manifest = self._knowledge_pack_manifest()
        constitution_metadata = self._constitution_metadata()

        source_lineage = best_record.get("source_lineage") or {}
        provenance = source_lineage.get("provenance_status", "")
        if provenance != "VERIFIED":
            raise ValueError(
                f"[SAFETY_GATE] Authority failure: provenance_status='{provenance}' "
                f"on record '{best_record.get('record_id')}'. "
                "Only VERIFIED records are permitted in the canonical runtime."
            )
        for field in ("publisher", "board", "isbn", "authority_signature", "verification_timestamp"):
            if not source_lineage.get(field):
                raise ValueError(
                    f"[SAFETY_GATE] Authority failure: missing '{field}' in source lineage "
                    f"for record '{best_record.get('record_id')}'."
                )

        # Gate 2: Evidence handle must be present
        if not evidence or not evidence.get("evidence_id"):
            raise ValueError(
                f"[SAFETY_GATE] Evidence failure: no evidence handle on record "
                f"'{best_record.get('record_id')}'. Evidence injection is mandatory."
            )

        # Gate 3: Lineage fields must be present
        for field in ("textbook_id", "edition", "chapter", "section", "lineage_hash"):
            if not evidence.get(field):
                raise ValueError(
                    f"[SAFETY_GATE] Lineage failure: missing '{field}' in evidence handle "
                    f"for record '{best_record.get('record_id')}'."
                )
        if not evidence.get("page_numbers"):
            raise ValueError(
                f"[SAFETY_GATE] Lineage failure: missing page_numbers in evidence handle "
                f"for record '{best_record.get('record_id')}'."
            )
        if evidence.get("lineage_hash") != self._expected_lineage_hash(evidence):
            raise ValueError(
                f"[SAFETY_GATE] Lineage failure: lineage_hash mismatch on record "
                f"'{best_record.get('record_id')}'."
            )

        # Gate 4: Content hash must exist
        if not evidence.get("source_hash"):
            raise ValueError(
                f"[SAFETY_GATE] Hash failure: missing 'source_hash' in evidence handle "
                f"for record '{best_record.get('record_id')}'."
            )
        if evidence.get("source_hash") != source_lineage.get("source_hash"):
            raise ValueError(
                f"[SAFETY_GATE] Hash failure: evidence source_hash does not match source lineage "
                f"for record '{best_record.get('record_id')}'."
            )

        if manifest.get("validation_status") != "ALL_VERIFIED":
            raise ValueError("[SAFETY_GATE] Version failure: canonical manifest is not ALL_VERIFIED.")
        if best_record.get("version") != best_record.get("curriculum_version"):
            raise ValueError(
                f"[SAFETY_GATE] Version failure: version and curriculum_version differ on "
                f"record '{best_record.get('record_id')}'."
            )
        if pack_manifest.get("dataset_hash") != manifest.get("dataset_hash"):
            raise ValueError("[SAFETY_GATE] Dataset signature failure: knowledge pack hash mismatch.")
        if not manifest.get("dataset_signature"):
            raise ValueError("[SAFETY_GATE] Dataset signature failure: manifest signature missing.")

        required_gates = {
            "authority",
            "evidence",
            "lineage",
            "hash",
            "version",
            "dataset_signature",
            "constitution",
            "runtime_contract",
        }
        configured_gates = set(constitution_metadata.get("safety_gates") or [])
        if not required_gates.issubset(configured_gates):
            raise ValueError("[SAFETY_GATE] Constitution failure: required safety gates are incomplete.")
        if constitution_metadata.get("failure_policy") != "refuse canonical execution":
            raise ValueError("[SAFETY_GATE] Constitution failure: refusal policy is not enforced.")

        # Gate 5: Governance — canonical_authority_granted must be True
        governance = best_record.get("governance") or {}
        if not governance.get("canonical_authority_granted", False):
            raise ValueError(
                f"[SAFETY_GATE] Governance failure: canonical_authority_granted=False "
                f"on record '{best_record.get('record_id')}'."
            )

    def execute(
        self,
        query: str,
        student_id: str = "ANONYMOUS",
        grade: Optional[int] = None,
        medium: Optional[str] = None,
        subject: Optional[str] = None,
        exercise_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a student query through the full canonical pipeline.

        Args:
            query:          Student's question string
            student_id:     Unique student identifier
            grade:          Optional grade filter
            medium:         Optional medium filter
            subject:        Optional subject filter
            exercise_result: Optional exercise outcome to record in mastery engine
                             format: { concept_id, correct, confidence, time_seconds }
        """
        request_id = str(uuid.uuid4())
        t_start = time.perf_counter()
        trace: List[Dict[str, Any]] = []

        # ── Stage 1: Retrieval ──────────────────────────────────────────────
        t0 = time.perf_counter()
        retrieval_payload = retrieve_from_masterdb(
            query=query, grade=grade, medium=medium, subject=subject
        )
        best_record = retrieval_payload.get("best_record") or {}
        retrieval_confidence = retrieval_payload.get("confidence", 0.0)

        # Extract evidence handle injected by retrieval engine
        evidence_handle = best_record.get("evidence") or {}

        # Production safety gates: no canonical match means no evidence chain.
        if not best_record:
            return self._blocked_contract(
                request_id=request_id,
                student_id=student_id,
                query=query,
                reason="[SAFETY_GATE] Evidence failure: no canonical retrieval match. Refusing execution.",
            )
        try:
            self._validate_production_gates(best_record, evidence_handle)
        except ValueError as gate_err:
            return self._blocked_contract(
                request_id=request_id,
                student_id=student_id,
                query=query,
                reason=str(gate_err),
            )

        trace.append({
            "stage": "retrieval",
            "matched": bool(best_record),
            "confidence": retrieval_confidence,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        })

        # ── Stage 2: Curriculum Intelligence ───────────────────────────────
        t0 = time.perf_counter()
        curriculum_intelligence = {
            "concept":            best_record.get("concept"),
            "chapter":            best_record.get("chapter"),
            "subject":            best_record.get("subject"),
            "definition":         best_record.get("definition"),
            "learning_outcome":   best_record.get("learning_outcome"),
            "source_lineage":     best_record.get("source_lineage"),
            "curriculum_version": best_record.get("curriculum_version"),
            "matched_record_id":  best_record.get("record_id"),
            "provenance_status":  (best_record.get("source_lineage") or {}).get("provenance_status"),
            # Evidence handle injected by retrieval engine — passed through to _bind_contract
            "evidence":           evidence_handle,
        }
        trace.append({
            "stage": "curriculum_intelligence",
            "concept_resolved": bool(curriculum_intelligence["concept"]),
            "lineage_present":  bool(curriculum_intelligence["source_lineage"]),
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        })

        # ── Stage 3: Learning Intelligence ─────────────────────────────────
        t0 = time.perf_counter()
        learning_payload = build_learning_intelligence(query, retrieval_payload)
        trace.append({
            "stage": "learning_intelligence",
            "gap_detected": bool(learning_payload.get("learning_gap")),
            "path_generated": bool(learning_payload.get("learning_path_suggestion")),
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        })

        # ── Stage 4: Mastery Intelligence ──────────────────────────────────
        t0 = time.perf_counter()
        mastery_engine = self._get_or_create_engine(student_id=student_id, grade=grade or 1)

        if exercise_result:
            mastery_engine.record_exercise(
                concept_id=exercise_result.get("concept_id", curriculum_intelligence.get("concept") or "UNKNOWN"),
                correct=exercise_result.get("correct", False),
                confidence=exercise_result.get("confidence", 0.5),
                time_seconds=exercise_result.get("time_seconds", 60),
            )

        mastery_state = mastery_engine.build_progress_state()
        trace.append({
            "stage": "mastery_intelligence",
            "mastery_score": mastery_state["mastery_score"],
            "weak_areas_count": len(mastery_state["weak_areas"]),
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        })

        # ── Stage 5: Constitutional Runtime ────────────────────────────────
        t0 = time.perf_counter()
        constitutional_output = None
        if self._rule_engine:
            try:
                constitutional_output = self._rule_engine.evaluate(
                    content=query,
                    metadata={"grade": grade, "subject": subject},
                    apply_enforcement=True,
                )
            except Exception as e:
                constitutional_output = {"decision": "error", "reason": str(e)}
        trace.append({
            "stage": "constitutional_runtime",
            "available": self._rule_engine is not None,
            "decision": (constitutional_output or {}).get("decision", "skipped"),
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        })

        # ── Stage 6: Runtime Contract ───────────────────────────────────────
        total_latency_ms = round((time.perf_counter() - t_start) * 1000, 2)

        runtime_contract = self._bind_contract(
            request_id=request_id,
            query=query,
            student_id=student_id,
            curriculum_intelligence=curriculum_intelligence,
            learning_payload=learning_payload,
            mastery_state=mastery_state,
            retrieval_confidence=retrieval_confidence,
            constitutional_output=constitutional_output,
            trace=trace,
            total_latency_ms=total_latency_ms,
        )

        return runtime_contract

    def _resolve_evidence(
        self,
        curriculum_intelligence: Dict[str, Any],
        retrieval_confidence: float,
        pre_built_evidence: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Returns the evidence handle already injected by the retrieval engine.
        Falls back to registry lookup only if the handle is absent (e.g. no-match path).
        """
        if pre_built_evidence:
            return pre_built_evidence
        raise ValueError("[SAFETY_GATE] Evidence failure: retrieval did not provide an evidence handle.")

    def _bind_contract(
        self,
        request_id: str,
        query: str,
        student_id: str,
        curriculum_intelligence: Dict[str, Any],
        learning_payload: Dict[str, Any],
        mastery_state: Dict[str, Any],
        retrieval_confidence: float,
        constitutional_output: Optional[Dict[str, Any]],
        trace: List[Dict[str, Any]],
        total_latency_ms: float,
    ) -> Dict[str, Any]:
        """Bind all stage outputs into the canonical runtime contract."""
        # Pass the pre-built evidence handle from retrieval (injected via evidence_first_retrieval)
        pre_built = curriculum_intelligence.get("evidence")
        evidence = self._resolve_evidence(curriculum_intelligence, retrieval_confidence, pre_built_evidence=pre_built)
        return {
            "request_id":            request_id,
            "timestamp":             datetime.now(timezone.utc).isoformat(),
            "schema_version":        "UNIGURU_CANONICAL_RUNTIME_V2",
            "student_id":            student_id,
            "query":                 query,
            # ── Evidence Contract Fields ──────────────────────────────────
            "evidence_id":           evidence["evidence_id"],
            "textbook_id":           evidence["textbook_id"],
            "edition":               evidence["edition"],
            "chapter":               evidence["chapter"],
            "section":               evidence["section"],
            "page_numbers":          evidence["page_numbers"],
            "source_hash":           evidence["source_hash"],
            "retrieval_hash":        evidence["retrieval_hash"],
            "lineage_hash":          evidence["lineage_hash"],
            "verification_status":   evidence["verification_status"],
            "runtime_evidence":      evidence,
            # ── Retrieval ────────────────────────────────────────────────
            "retrieval": {
                "matched":              bool(curriculum_intelligence.get("matched_record_id")),
                "confidence":           retrieval_confidence,
                "matched_record_id":    curriculum_intelligence.get("matched_record_id"),
                "chapter":              curriculum_intelligence.get("chapter"),
                "subject":              curriculum_intelligence.get("subject"),
            },
            # ── Curriculum Intelligence ──────────────────────────────────
            "curriculum_intelligence": curriculum_intelligence,
            # ── Learning Intelligence ────────────────────────────────────
            "learning_intelligence": {
                "learning_outcome":       learning_payload.get("learning_outcome"),
                "learning_gap":           learning_payload.get("learning_gap"),
                "learning_path":          learning_payload.get("learning_path_suggestion"),
                "practice_recommendations": learning_payload.get("practice_recommendations", []),
                "remediation_recommendation": learning_payload.get("remediation_recommendation"),
            },
            # ── Mastery Intelligence (runtime output contract fields) ────
            "mastery_score":           mastery_state["mastery_score"],
            "concept_strengths":       mastery_state["concept_strengths"],
            "concept_weaknesses":      mastery_state["concept_weaknesses"],
            "recommended_remediation": mastery_state["recommended_remediation"],
            "learning_progress_state": mastery_state["learning_progress_state"],
            "mastery_level":           mastery_state["mastery_level"],
            "weak_areas":              mastery_state["weak_areas"],
            # ── Constitutional Runtime ────────────────────────────────────
            "constitutional_runtime": {
                "active":    constitutional_output is not None,
                "decision":  (constitutional_output or {}).get("decision", "skipped"),
                "enforced":  (constitutional_output or {}).get("enforced", False),
            },
            # ── Pipeline Trace ────────────────────────────────────────────
            "pipeline_trace":  trace,
            "total_latency_ms": total_latency_ms,
            "pipeline_stages": [
                "StudentQuery",
                "Retrieval",
                "CurriculumIntelligence",
                "LearningIntelligence",
                "MasteryIntelligence",
                "ConstitutionalRuntime",
                "RuntimeContract",
            ],
            "convergence_validated": True,
        }


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------

_runtime_instance: Optional[CanonicalRuntime] = None


def get_canonical_runtime() -> CanonicalRuntime:
    global _runtime_instance
    if _runtime_instance is None:
        _runtime_instance = CanonicalRuntime()
    return _runtime_instance


def execute_query(
    query: str,
    student_id: str = "ANONYMOUS",
    grade: Optional[int] = None,
    medium: Optional[str] = None,
    subject: Optional[str] = None,
    exercise_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convenience wrapper for the canonical runtime."""
    return get_canonical_runtime().execute(
        query=query,
        student_id=student_id,
        grade=grade,
        medium=medium,
        subject=subject,
        exercise_result=exercise_result,
    )


if __name__ == "__main__":
    result = execute_query(
        query="What is counting?",
        student_id="DEMO_STUDENT",
        grade=1,
        subject="Mathematics",
    )
    print(json.dumps(result, indent=2, default=str))
