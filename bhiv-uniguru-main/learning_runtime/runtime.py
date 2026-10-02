from __future__ import annotations

from typing import Any, Dict, Optional

from retrieval.retrieval_engine import retrieve_from_masterdb
from .learning_intelligence import build_learning_intelligence


def build_learning_runtime(
    question: str,
    grade: Optional[int] = None,
    medium: Optional[str] = None,
    subject: Optional[str] = None,
) -> Dict[str, Any]:
    retrieval_payload = retrieve_from_masterdb(question, grade, medium, subject)
    learning_payload = build_learning_intelligence(question, retrieval_payload)
    record = retrieval_payload.get("best_record") or {}
    matched = bool(record)

    return {
        "student_question": question,
        "retrieval": {
            "matched": matched,
            "grade": grade,
            "medium": medium,
            "subject": subject,
            "retrieval_confidence": retrieval_payload.get("confidence", 0.0),
            "matched_record_id": record.get("record_id"),
            "chapter_recommendations": retrieval_payload.get("chapter_recommendations", []),
        },
        "concept_match": {
            "concept": record.get("concept"),
            "chapter": record.get("chapter"),
            "subject": record.get("subject"),
            "learning_outcome": learning_payload.get("learning_outcome"),
        },
        "curriculum_mapping": learning_payload.get("curriculum_mapping"),
        "explanation": retrieval_payload.get("best_record") and retrieval_payload.get("best_record").get("definition"),
        "learning_state": learning_payload,
        "trace_artifact": {
            "retrieval_hash": retrieval_payload.get("retrieval_hash"),
            "schema_version": "UNIGURU_LEARNING_RUNTIME_V1",
        },
    }
