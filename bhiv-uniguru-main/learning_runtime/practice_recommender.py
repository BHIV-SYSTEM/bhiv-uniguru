from __future__ import annotations

from typing import Any, Dict, List


def recommend_practice(record: Dict[str, Any], related_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    practice_questions = []
    if record:
        practice_questions.extend(record.get("questions") or [])
    for related in related_records[:3]:
        if related and related.get("questions"):
            practice_questions.extend(related.get("questions")[:2])

    difficulty_progression = []
    difficulty = record.get("difficulty")
    if difficulty == "easy":
        difficulty_progression = ["easy", "medium", "hard"]
    elif difficulty == "medium":
        difficulty_progression = ["medium", "hard"]
    elif difficulty == "hard":
        difficulty_progression = ["hard", "medium"]
    else:
        difficulty_progression = ["easy", "medium", "hard"]

    return {
        "practice_questions": practice_questions[:5],
        "difficulty_progression": difficulty_progression,
        "practice_focus": (
            "Reinforce the matched concept with mixed practice from related curriculum records."
            if related_records
            else "Practice the matched concept thoroughly before progressing."
        ),
    }
