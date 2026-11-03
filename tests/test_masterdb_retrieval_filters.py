import pytest

from retrieval import retrieval_engine


@pytest.fixture
def masterdb_record():
    return {
        "record_id": "BALBHARTI_MATH_G1_MM_CONCEPT_TEST",
        "grade": 1,
        "medium": "Marathi Medium",
        "subject": "Mathematics",
        "chapter": "Counting",
        "concept": "counting numbers",
        "definition": "Counting numbers represent a count.",
        "learning_outcome": "Count numbers.",
        "examples": ["Count one to five."],
        "questions": ["How many objects are there?"],
        "difficulty": "easy",
        "source_lineage": {"source_reference": "test-only"},
        "curriculum_version": "test-v1",
    }


@pytest.mark.parametrize(
    "filters",
    [
        {"grade": 2},
        {"medium": "English Medium"},
        {"subject": "Science"},
    ],
)
def test_masterdb_retrieval_does_not_fall_back_outside_explicit_filters(
    monkeypatch, masterdb_record, filters
):
    monkeypatch.setattr(retrieval_engine, "load_masterdb_records", lambda: [masterdb_record])

    result = retrieval_engine.find_top_matches("counting", **filters)

    assert result["matches"] == []
    assert result["best_record"] is None


def test_masterdb_retrieval_keeps_records_matching_explicit_filters(
    monkeypatch, masterdb_record
):
    monkeypatch.setattr(retrieval_engine, "load_masterdb_records", lambda: [masterdb_record])

    result = retrieval_engine.find_top_matches(
        "counting", grade=1, medium="Marathi Medium", subject="Mathematics"
    )

    assert result["best_record"]["record_id"] == masterdb_record["record_id"]
