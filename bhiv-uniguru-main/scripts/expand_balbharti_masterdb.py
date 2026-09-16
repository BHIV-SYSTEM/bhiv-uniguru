from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
BALBHARTI_DIR = ROOT / "masterdb" / "balbharti"
DATASET_PATH = BALBHARTI_DIR / "sample_ingestion_dataset.json"

SUBJECTS = [
    "Mathematics",
    "Science",
    "EVS",
    "History",
    "Geography",
    "Marathi",
    "English",
    "Civics",
]

COMMON_CHAPTERS = {
    "Mathematics": [
        "Numbers", "Shapes", "Patterns", "Measurement", "Fractions", "Data", "Algebra", "Geometry"
    ],
    "Science": [
        "Living Things", "Matter", "Energy", "Our Earth", "Plants", "Force and Motion", "Health", "Space"
    ],
    "EVS": [
        "My Family", "Food and Nutrition", "Water", "Air", "Safety", "Community", "Festivals", "Weather"
    ],
    "History": [
        "Early People", "Ancient India", "Medieval India", "Freedom Movement", "Local History", "National Leaders", "Modern India", "Heritage"
    ],
    "Geography": [
        "Maps", "Natural Resources", "Climate", "Soil", "Rivers", "Mountains", "Population", "Environment"
    ],
    "Marathi": [
        "Akshar Odh", "Vyakaran", "Kathaa", "Kavitva", "Lekhankan", "Vachanan", "Bolicha Abhyas", "Rachana"
    ],
    "English": [
        "Letters", "Words", "Stories", "Poems", "Grammar", "Reading", "Writing", "Listening"
    ],
    "Civics": [
        "Rights", "Duties", "Government", "Local Community", "Constitution", "Public Services", "Environment", "Civic Life"
    ],
}

DIFFICULTY_CYCLE = ["easy", "medium", "hard"]

MEDIUMS = ["English Medium", "Marathi Medium"]

def _build_learning_outcome(subject: str, chapter: str, grade: int) -> str:
    return (
        f"Students will learn the key idea of {chapter} in {subject} for grade {grade}, "
        "build foundational understanding, and apply it through curriculum exercises."
    )


def _build_definition(subject: str, chapter: str, grade: int, index: int, medium: str) -> str:
    return (
        f"This concept explains {chapter} within the {subject} curriculum for grade {grade}. "
        f"It is presented with age-appropriate examples and guided practice for {medium}."
    )


def _build_examples(subject: str, chapter: str, index: int) -> List[str]:
    return [
        f"Example {index + 1}: Use {chapter} to solve a simple grade-level problem.",
        f"Example {index + 2}: Observe how {chapter} appears in everyday life."
    ]


def _build_questions(subject: str, chapter: str, grade: int, index: int) -> List[str]:
    return [
        f"What is one important idea from {chapter}?",
        f"How does {chapter} relate to grade {grade} {subject.lower()} learning?"
    ]


def _build_source_lineage(subject: str, grade: int, medium: str, chapter: str) -> Dict[str, Any]:
    return {
        "publisher": "Maharashtra State Bureau of Textbook Production and Curriculum Research",
        "source_type": "curriculum_sample_seed",
        "source_reference": f"Balbharti {medium} Class {grade} {subject}",
        "page_or_section": f"{chapter} mapping",
        "ingestion_method": "synthetic_expansion_seed",
        "provenance_status": "sample_seed",
    }


def build_records() -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for grade in range(1, 11):
        for medium in MEDIUMS:
            for subject in SUBJECTS:
                chapter_list = COMMON_CHAPTERS[subject]
                for chapter_index, chapter in enumerate(chapter_list):
                    for item_index in range(2):
                        record = {
                            "record_id": (
                                f"balbharti_{'en' if medium=='English Medium' else 'mr'}_g{grade}_"
                                f"{subject.lower()}_{chapter.lower().replace(' ', '_')}_{chapter_index + 1}_{item_index + 1:02}"
                            ),
                            "grade": grade,
                            "medium": medium,
                            "subject": subject,
                            "chapter": chapter,
                            "concept": f"{chapter} concept {item_index + 1}",
                            "definition": _build_definition(subject, chapter, grade, item_index, medium),
                            "learning_outcome": _build_learning_outcome(subject, chapter, grade),
                            "examples": _build_examples(subject, chapter, item_index),
                            "questions": _build_questions(subject, chapter, grade, item_index),
                            "difficulty": DIFFICULTY_CYCLE[(grade + chapter_index + item_index) % len(DIFFICULTY_CYCLE)],
                            "language_variant": "en-IN" if medium == "English Medium" else "mr-IN",
                            "source_lineage": _build_source_lineage(subject, grade, medium, chapter),
                            "curriculum_version": "balbharti-2026-06",
                            "version": "balbharti-2026-06",
                            "governance": {
                                "canonical_authority_granted": False,
                                "review_required": True,
                                "replay_safe": True,
                            },
                        }
                        records.append(record)
    return records


def main() -> None:
    BALBHARTI_DIR.mkdir(parents=True, exist_ok=True)
    records = build_records()
    DATASET_PATH.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated {len(records)} Balbharti masterdb records at {DATASET_PATH}")


if __name__ == "__main__":
    main()
