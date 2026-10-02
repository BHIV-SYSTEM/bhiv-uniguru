from __future__ import annotations

from typing import Any, Dict


def detect_learning_gaps(question: str, record: Dict[str, Any], retrieval: Dict[str, Any]) -> Dict[str, Any]:
    if not record:
        return {
            "gap_type": "curriculum_mapping_gap",
            "description": "No close curriculum record was matched for the query.",
            "remediation_recommendation": "Collect the grade, medium, subject, and chapter from the student question and map it to Balbharti curriculum entries.",
            "confidence": retrieval.get("confidence", 0.0),
        }

    confidence = retrieval.get("confidence", 0.0)
    difficulty = record.get("difficulty") or "medium"
    grade = int(record.get("grade") or 0)

    if confidence < 0.5:
        recommendation = (
            "The curriculum match is weak. Review the chapter title and learning outcomes, then try a more specific question."
        )
    elif difficulty == "hard":
        recommendation = (
            "This topic is advanced for the matched grade. Start with the earlier foundational concept and then revisit this chapter."
        )
    else:
        recommendation = (
            "Review the matched concept in class and then practice the suggested questions for mastery."
        )

    return {
        "gap_type": "conceptual_reinforcement" if confidence >= 0.5 else "mapping_uncertainty",
        "description": f"Matched grade {grade} topic with {difficulty} difficulty and confidence {confidence:.2f}.",
        "remediation_recommendation": recommendation,
        "confidence": confidence,
    }
