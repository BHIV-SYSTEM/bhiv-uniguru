from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List

from backend.memory.constitutional_semantic_memory import stable_hash, utc_now_iso


EXPECTED_GRADES = set(range(1, 11))
EXPECTED_MEDIUMS = {"English Medium", "Marathi Medium"}
EXPECTED_SUBJECTS = {
    "Mathematics",
    "Science",
    "EVS",
    "History",
    "Geography",
    "Marathi",
    "English",
    "Civics",
}

REQUIRED_FIELDS = {
    "record_id",
    "grade",
    "medium",
    "subject",
    "chapter",
    "concept",
    "definition",
    "learning_outcome",
    "examples",
    "questions",
    "difficulty",
    "source_lineage",
    "curriculum_version",
}


def validate_masterdb(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(records)
    record_ids = [str(record.get("record_id")) for record in rows]
    duplicate_ids = sorted(record_id for record_id, count in Counter(record_ids).items() if count > 1)
    invalid_rows: List[Dict[str, Any]] = []
    provenance_counts: Counter[str] = Counter()
    version_counts: Counter[str] = Counter()
    chapter_index: dict[str, set[str]] = defaultdict(set)

    for record in rows:
        lineage = record.get("source_lineage") if isinstance(record.get("source_lineage"), dict) else {}
        governance = record.get("governance") if isinstance(record.get("governance"), dict) else {}
        issues: List[str] = []
        missing = sorted(REQUIRED_FIELDS - set(record))
        if missing:
            issues.append(f"missing_fields:{','.join(missing)}")
        if record.get("medium") not in EXPECTED_MEDIUMS:
            issues.append("unsupported_medium")
        if int(record.get("grade") or 0) not in EXPECTED_GRADES:
            issues.append("unsupported_grade")
        if record.get("subject") not in EXPECTED_SUBJECTS:
            issues.append("unsupported_subject")
        if not lineage.get("source_reference"):
            issues.append("missing_source_reference")
        if lineage.get("provenance_status") == "sample_seed" and governance.get("canonical_authority_granted") is True:
            issues.append("sample_seed_cannot_grant_canonical_authority")

        provenance_counts[str(lineage.get("provenance_status") or "unknown")] += 1
        version_counts[str(record.get("curriculum_version") or "unknown")] += 1
        chapter_index[f"{record.get('medium')}|G{record.get('grade')}|{record.get('subject')}"].add(str(record.get("chapter")))

        if issues:
            invalid_rows.append(
                {
                    "record_id": record.get("record_id"),
                    "issues": issues,
                    "record_hash": stable_hash(record),
                }
            )

    missing_chapter_groups = [
        {"group": group, "chapter_count": len(chapters)}
        for group, chapters in sorted(chapter_index.items())
        if len(chapters) < 4
    ]
    report = {
        "schema": "UNIGURU_CURRICULUM_INTEGRITY_REPORT_V1",
        "generated_at": utc_now_iso(),
        "record_count": len(rows),
        "valid_record_count": len(rows) - len(invalid_rows),
        "duplicate_record_ids": duplicate_ids,
        "invalid_rows": invalid_rows[:50],
        "provenance_counts": dict(sorted(provenance_counts.items())),
        "curriculum_versions": dict(sorted(version_counts.items())),
        "missing_chapter_detection": {
            "minimum_expected_chapters_per_grade_subject_medium": 4,
            "groups_below_minimum": missing_chapter_groups,
            "groups_below_minimum_count": len(missing_chapter_groups),
        },
        "canonical_authority_granted": False,
        "validation_hash": "",
    }
    report["validation_hash"] = stable_hash(report)
    return report
