from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
BALBHARTI_DIR = ROOT / "masterdb" / "balbharti"
DATASET = BALBHARTI_DIR / "sample_ingestion_dataset.json"
MANIFEST = BALBHARTI_DIR / "ingestion_manifest.json"
COVERAGE_REPORT = ROOT / "curriculum" / "coverage_report.json"
MASTERDB_DASHBOARD = ROOT / "masterdb" / "masterdb_dashboard.json"
PROOF = ROOT / "review_packets" / "proof_logs" / "balbharti_masterdb_ingestion_proof.json"
INTEGRITY_REPORT = ROOT / "review_packets" / "proof_logs" / "curriculum_integrity_report.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from memory.constitutional_semantic_memory import stable_hash, utc_now_iso
from masterdb.coverage_validator import build_coverage_report
from masterdb.masterdb_validation import validate_masterdb


REQUIRED_FIELDS = {
    "record_id",
    "grade",
    "medium",
    "subject",
    "chapter",
    "concept",
    "definition",
    "examples",
    "questions",
    "language_variant",
    "source_lineage",
    "curriculum_version",
}


def load_records() -> List[Dict[str, Any]]:
    records = json.loads(DATASET.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("Balbharti dataset must be a JSON list.")
    return records


def validate_record(record: Dict[str, Any]) -> Dict[str, Any]:
    missing = sorted(REQUIRED_FIELDS - set(record))
    lineage = record.get("source_lineage") if isinstance(record.get("source_lineage"), dict) else {}
    governance = record.get("governance") if isinstance(record.get("governance"), dict) else {}
    issues = []
    if missing:
        issues.append({"type": "missing_required_fields", "fields": missing})
    if record.get("medium") not in {"Marathi Medium", "English Medium"}:
        issues.append({"type": "unsupported_medium", "medium": record.get("medium")})
    if int(record.get("grade") or 0) < 1 or int(record.get("grade") or 0) > 10:
        issues.append({"type": "unsupported_grade", "grade": record.get("grade")})
    if lineage.get("provenance_status") == "sample_seed" and governance.get("canonical_authority_granted") is True:
        issues.append({"type": "sample_seed_cannot_grant_canonical_authority"})
    return {
        "record_id": record.get("record_id"),
        "record_hash": stable_hash(record),
        "valid": not issues,
        "issues": issues,
        "medium": record.get("medium"),
        "grade": record.get("grade"),
        "subject": record.get("subject"),
        "source_reference": lineage.get("source_reference"),
        "canonical_authority_granted": bool(governance.get("canonical_authority_granted")),
    }


def build_manifest(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = [validate_record(record) for record in records]
    mediums = sorted({str(record.get("medium")) for record in records})
    grades = sorted({int(record.get("grade") or 0) for record in records})
    subjects = sorted({str(record.get("subject")) for record in records})
    manifest = {
        "schema": "UNIGURU_BALBHARTI_MASTERDB_INGESTION_MANIFEST_V1",
        "generated_at": utc_now_iso(),
        "dataset_path": str(DATASET.relative_to(ROOT).as_posix()),
        "record_count": len(records),
        "valid_record_count": sum(1 for row in rows if row["valid"]),
        "mediums": mediums,
        "grades": grades,
        "subjects": subjects,
        "priority_band_coverage": {
            "primary_1_5_present": any(1 <= int(grade) <= 5 for grade in grades),
            "secondary_6_10_present": any(6 <= int(grade) <= 10 for grade in grades),
        },
        "records": rows,
        "canonical_authority_granted": False,
        "replay_safe": all(row["valid"] for row in rows),
    }
    manifest["dataset_hash"] = stable_hash(records)
    manifest["manifest_hash"] = stable_hash(manifest)
    return manifest


def build_masterdb_dashboard(records: list[dict]) -> dict[str, any]:
    grades = sorted({int(record.get("grade") or 0) for record in records})
    subjects = sorted({str(record.get("subject")) for record in records})
    mediums = sorted({str(record.get("medium")) for record in records})
    chapters = sorted({str(record.get("chapter")) for record in records})
    rows: dict[str, int] = {}
    for record in records:
        key = f"{record.get('subject')}-Grade{record.get('grade')}"
        rows[key] = rows.get(key, 0) + 1

    coverage_missing = {
        "grades": [grade for grade in range(1, 11) if grade not in grades],
        "subjects": [subject for subject in ["Mathematics", "Science", "EVS", "History", "Geography", "Marathi", "English", "Civics"] if subject not in subjects],
        "full_balbharti_standards_1_10": len(grades) == 10 and len(subjects) >= 8,
        "description": "Expanded dataset coverage includes the core Balbharti grade-subject space for this sprint. Missing subjects or grades indicate areas needing verified textbook ingestion.",
    }
    return {
        "schema": "UNIGURU_MASTERDB_DASHBOARD_V1",
        "generated_at": utc_now_iso(),
        "subjects": subjects,
        "grades": grades,
        "chapters": chapters,
        "records_by_grade_subject": rows,
        "current_ingestion_summary": {
            "record_count": len(records),
            "mediums": mediums,
            "sample_seed_only": True,
            "source_lineage_types": sorted({(record.get("source_lineage") or {}).get("source_type") for record in records}),
        },
        "coverage_missing": coverage_missing,
    }


def build_curriculum_coverage_report(records: list[dict]) -> dict[str, any]:
    grades = sorted({int(record.get("grade") or 0) for record in records})
    subjects = sorted({str(record.get("subject")) for record in records})
    chapters = sorted({str(record.get("chapter")) for record in records})
    concepts = sorted({str(record.get("concept")) for record in records})
    missing_grades = [grade for grade in range(1, 11) if grade not in grades]
    missing_subjects = [subject for subject in ["Mathematics", "Science", "EVS", "History", "Geography", "Marathi", "English", "Civics"] if subject not in subjects]
    return {
        "schema": "UNIGURU_BALBHARTI_CURRICULUM_COVERAGE_REPORT_V1",
        "generated_at": utc_now_iso(),
        "record_count": len(records),
        "mediums": sorted({str(record.get("medium")) for record in records}),
        "subjects": subjects,
        "grades": grades,
        "chapters": chapters,
        "concepts": concepts,
        "missing_coverage": {
            "expected_grade_range": [1, 10],
            "grades_not_ingested": missing_grades,
            "subjects_not_ingested": missing_subjects,
            "mediums_not_ingested": [],
            "notes": "The dataset has been synthetically expanded for sprint convergence. Verify textbook-level coverage before production deployment.",
        },
        "curriculum_version": "balbharti-2026-06",
    }


def main() -> None:
    records = load_records()
    manifest = build_manifest(records)
    coverage = build_coverage_report(records)
    integrity = validate_masterdb(records)
    MASTERDB_DASHBOARD.write_text(json.dumps(build_masterdb_dashboard(records), indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    COVERAGE_REPORT.write_text(json.dumps({**build_curriculum_coverage_report(records), "coverage_validation": coverage}, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    PROOF.parent.mkdir(parents=True, exist_ok=True)
    PROOF.write_text(json.dumps(manifest, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    INTEGRITY_REPORT.write_text(json.dumps(integrity, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": manifest["schema"],
                "record_count": manifest["record_count"],
                "valid_record_count": manifest["valid_record_count"],
                "grades": manifest["grades"],
                "mediums": manifest["mediums"],
                "subjects": manifest["subjects"],
                "dataset_hash": manifest["dataset_hash"],
                "manifest_hash": manifest["manifest_hash"],
                "coverage_percent": coverage["coverage_percent"],
                "integrity_validation_hash": integrity["validation_hash"],
                "canonical_authority_granted": manifest["canonical_authority_granted"],
                "replay_safe": manifest["replay_safe"],
            },
            indent=2,
            ensure_ascii=True,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
