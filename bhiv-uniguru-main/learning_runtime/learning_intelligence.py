from __future__ import annotations

from typing import Any, Dict, List

from .learning_gap_detector import detect_learning_gaps
from .learning_path_generator import generate_learning_path
from .practice_recommender import recommend_practice


def build_learning_intelligence(question: str, retrieval: Dict[str, Any]) -> Dict[str, Any]:
    record = retrieval.get("best_record") or {}
    related_records = retrieval.get("related_records") or []
    curriculum_graph = retrieval.get("curriculum_graph") or {}

    learning_outcome = record.get("learning_outcome") or (
        f"Understand the curriculum concept {record.get('concept') or 'selected topic'} through Balbharti-guided learning."
    )
    learning_path = generate_learning_path(record, curriculum_graph)
    gap = detect_learning_gaps(question, record, retrieval)
    practice = recommend_practice(record, related_records)

    follow_up_concepts: List[str] = []
    if related_records:
        follow_up_concepts = [f"Explore: {related.get('concept')}" for related in related_records[:4]]
    elif record.get("concept"):
        follow_up_concepts = [f"Review the chapter {record.get('chapter')}", f"Practice the concept {record.get('concept')} again"]
    else:
        follow_up_concepts = [
            "Identify the grade-level curriculum chapter for this question.",
            "Collect relevant Balbharti learning outcomes.",
        ]

    dependency_map = {
        "current_concept": record.get("concept"),
        "prerequisite_concept": learning_path.get("prerequisite_concept"),
        "next_concept": learning_path.get("next_concept"),
    }

    return {
        "learning_outcome": learning_outcome,
        "follow_up_concepts": follow_up_concepts,
        "practice_recommendations": practice.get("practice_questions", []),
        "remediation_recommendation": gap.get("remediation_recommendation"),
        "learning_path_suggestion": learning_path,
        "learning_gap": gap,
        "difficulty_progression": practice.get("difficulty_progression", []),
        "concept_dependency_map": dependency_map,
        "curriculum_mapping": {
            "matched_record_id": record.get("record_id"),
            "source_lineage": record.get("source_lineage"),
            "curriculum_version": record.get("curriculum_version"),
            "version": record.get("version"),
            "provenance_status": (record.get("source_lineage") or {}).get("provenance_status"),
        },
    }
