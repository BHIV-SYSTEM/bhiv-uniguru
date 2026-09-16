from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable

from backend.memory.constitutional_semantic_memory import stable_hash, utc_now_iso
from masterdb.masterdb_validation import EXPECTED_GRADES, EXPECTED_MEDIUMS, EXPECTED_SUBJECTS


def build_coverage_report(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(records)
    grades = {int(record.get("grade") or 0) for record in rows}
    subjects = {str(record.get("subject")) for record in rows}
    mediums = {str(record.get("medium")) for record in rows}
    subject_counts = Counter(str(record.get("subject")) for record in rows)
    grade_counts = Counter(str(record.get("grade")) for record in rows)
    medium_counts = Counter(str(record.get("medium")) for record in rows)

    expected_cells = len(EXPECTED_GRADES) * len(EXPECTED_SUBJECTS) * len(EXPECTED_MEDIUMS)
    present_cells = {
        (int(record.get("grade") or 0), str(record.get("subject")), str(record.get("medium")))
        for record in rows
    }
    missing_cells = [
        {"grade": grade, "subject": subject, "medium": medium}
        for grade in sorted(EXPECTED_GRADES)
        for subject in sorted(EXPECTED_SUBJECTS)
        for medium in sorted(EXPECTED_MEDIUMS)
        if (grade, subject, medium) not in present_cells
    ]

    report = {
        "schema": "UNIGURU_BALBHARTI_COVERAGE_VALIDATION_V1",
        "generated_at": utc_now_iso(),
        "record_count": len(rows),
        "coverage_percent": round((len(present_cells) / expected_cells) * 100, 2),
        "expected_grade_subject_medium_cells": expected_cells,
        "present_grade_subject_medium_cells": len(present_cells),
        "grades_covered": sorted(grades),
        "subjects_covered": sorted(subjects),
        "mediums_covered": sorted(mediums),
        "missing_grades": sorted(EXPECTED_GRADES - grades),
        "missing_subjects": sorted(EXPECTED_SUBJECTS - subjects),
        "missing_mediums": sorted(EXPECTED_MEDIUMS - mediums),
        "missing_cells": missing_cells,
        "records_by_subject": dict(sorted(subject_counts.items())),
        "records_by_grade": dict(sorted(grade_counts.items())),
        "records_by_medium": dict(sorted(medium_counts.items())),
        "coverage_hash": "",
    }
    report["coverage_hash"] = stable_hash(report)
    return report
