from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_DATASET = ROOT / "masterdb" / "balbharti" / "canonical_dataset.json"
CANONICAL_MANIFEST = ROOT / "masterdb" / "balbharti" / "canonical_dataset_manifest.json"
AUTHORITY_REGISTRY = ROOT / "curriculum" / "authority" / "verified_textbook_authority_registry.json"
PAGE_REGISTRY = ROOT / "curriculum" / "provenance" / "page_registry.json"
EXPANSION_DIR = ROOT / "curriculum" / "production_expansion"
ASSIGNMENT_MANIFEST = EXPANSION_DIR / "assigned_textbooks_manifest.json"
EXPANSION_REPORT = EXPANSION_DIR / "production_expansion_report.json"
CROSS_VALIDATION_REPORT = EXPANSION_DIR / "vijay_cross_validation_report.json"
TEXTBOOK_DROP_README = ROOT / "masterdb" / "balbharti" / "licensed_textbooks" / "README.md"

SYNTHETIC_MARKERS = ("synthetic", "sample_seed", "placeholder", "dummy", "mock")
REQUIRED_RECORD_FIELDS = {
    "record_id",
    "grade",
    "medium",
    "subject",
    "chapter",
    "concept",
    "learning_outcome",
    "exercise_mapping",
    "source_lineage",
    "governance",
    "evidence",
}
REQUIRED_LINEAGE_FIELDS = {
    "publisher",
    "board",
    "edition",
    "isbn",
    "subject",
    "grade",
    "medium",
    "chapter",
    "section",
    "page",
    "source_hash",
    "authority_signature",
    "verification_timestamp",
    "provenance_status",
}
REQUIRED_EVIDENCE_FIELDS = {
    "evidence_id",
    "textbook_id",
    "edition",
    "chapter",
    "section",
    "page_numbers",
    "source_hash",
    "retrieval_hash",
    "lineage_hash",
    "verification_status",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")


def stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def contains_synthetic_marker(payload: Any) -> bool:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True).lower()
    return any(marker in raw for marker in SYNTHETIC_MARKERS)


def ensure_assignment_manifest(authority: dict[str, Any]) -> dict[str, Any]:
    if ASSIGNMENT_MANIFEST.exists():
        return load_json(ASSIGNMENT_MANIFEST)

    textbooks = authority.get("textbooks", [])
    manifest = {
        "schema": "UNIGURU_PRODUCTION_EXPANSION_ASSIGNMENT_MANIFEST_V1",
        "generated_at": utc_now_iso(),
        "sprint_id": "AI_NORMALIZED_CURRICULUM_EXPANSION_2026_06_25",
        "confidentiality": "Licensed curriculum assets remain outside committed source control.",
        "licensed_textbook_drop_root": "masterdb/balbharti/licensed_textbooks/",
        "assigned_to_codex": [
            {
                "textbook_id": row["textbook_id"],
                "publisher": row["publisher"],
                "board": "Maharashtra State Board",
                "medium": row["medium"],
                "class": row["grade"],
                "subject": row["subject"],
                "edition": row["edition"],
                "status": "already_in_canonical_snapshot",
                "source": "curriculum/authority/verified_textbook_authority_registry.json",
            }
            for row in textbooks
        ],
        "assigned_to_vijay": [],
        "known_unknowns": [
            "Remaining licensed textbooks pending ingestion",
            "OCR quality variations",
            "Cross-medium validation completion",
        ],
        "production_merge_policy": {
            "requires_codex_validation": True,
            "requires_vijay_validation": True,
            "requires_textbook_evidence": True,
            "requires_no_synthetic_or_placeholder_records": True,
            "requires_certification_pipeline_pass": True,
        },
    }
    manifest["assignment_hash"] = stable_hash(manifest)
    write_json(ASSIGNMENT_MANIFEST, manifest)
    return manifest


def ensure_textbook_drop_readme() -> None:
    TEXTBOOK_DROP_README.parent.mkdir(parents=True, exist_ok=True)
    if TEXTBOOK_DROP_README.exists():
        return
    TEXTBOOK_DROP_README.write_text(
        "\n".join(
            [
                "# Licensed Balbharti Textbook Drop",
                "",
                "Licensed textbook binaries are confidential BHIV ecosystem assets and must not be committed.",
                "Place acquired files under the deterministic hierarchy below before running production ingestion:",
                "",
                "```text",
                "masterdb/balbharti/licensed_textbooks/",
                "  <publisher>/",
                "    <board>/",
                "      <medium>/",
                "        class_<class>/",
                "          <subject>/",
                "            edition_<edition>/",
                "              source.pdf",
                "              source.sha256",
                "              acquisition_receipt.json",
                "              samachar_extraction.json",
                "              validation_evidence.json",
                "```",
                "",
                "Production gates require publisher authority, source hash, page evidence, lineage hash,",
                "retrieval hash, OCR status, and independent Vijay/Codex cross-validation before merge.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def page_lookup(pages: list[dict[str, Any]]) -> dict[tuple[str, str, int], dict[str, Any]]:
    lookup = {}
    for page in pages:
        lookup[(page["textbook_id"], str(page["edition"]), int(page["page_number"]))] = page
    return lookup


def validate_record(record: dict[str, Any], authorities: dict[str, dict[str, Any]], pages: dict[tuple[str, str, int], dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    missing = sorted(REQUIRED_RECORD_FIELDS - set(record))
    if missing:
        issues.append({"type": "missing_record_fields", "fields": missing})

    lineage = record.get("source_lineage") if isinstance(record.get("source_lineage"), dict) else {}
    evidence = record.get("evidence") if isinstance(record.get("evidence"), dict) else {}
    governance = record.get("governance") if isinstance(record.get("governance"), dict) else {}

    missing_lineage = sorted(REQUIRED_LINEAGE_FIELDS - set(lineage))
    if missing_lineage:
        issues.append({"type": "missing_lineage_fields", "fields": missing_lineage})
    missing_evidence = sorted(REQUIRED_EVIDENCE_FIELDS - set(evidence))
    if missing_evidence:
        issues.append({"type": "missing_evidence_fields", "fields": missing_evidence})

    textbook_id = evidence.get("textbook_id")
    authority = authorities.get(str(textbook_id))
    if not authority:
        issues.append({"type": "textbook_not_in_authority_registry", "textbook_id": textbook_id})
    elif authority.get("authority_status") != "VERIFIED_AUTHORITY":
        issues.append({"type": "textbook_authority_not_verified", "textbook_id": textbook_id})

    if evidence.get("verification_status") != "VERIFIED":
        issues.append({"type": "evidence_not_verified", "record_id": record.get("record_id")})
    if lineage.get("provenance_status") != "VERIFIED":
        issues.append({"type": "provenance_not_verified", "record_id": record.get("record_id")})
    if governance.get("canonical_authority_granted") is not True:
        issues.append({"type": "canonical_authority_not_granted", "record_id": record.get("record_id")})
    if not record.get("exercise_mapping"):
        issues.append({"type": "missing_exercise_mapping", "record_id": record.get("record_id")})
    if contains_synthetic_marker(record):
        issues.append({"type": "synthetic_or_placeholder_marker_detected", "record_id": record.get("record_id")})

    for page_number in evidence.get("page_numbers", []):
        page_key = (str(textbook_id), str(evidence.get("edition")), int(page_number))
        page = pages.get(page_key)
        if not page:
            issues.append({"type": "page_not_in_registry", "record_id": record.get("record_id"), "page": page_number})
            continue
        if page.get("ocr_status") != "VERIFIED":
            issues.append({"type": "page_ocr_not_verified", "record_id": record.get("record_id"), "page": page_number})
        if page.get("content_hash") != evidence.get("source_hash"):
            issues.append({"type": "page_hash_mismatch", "record_id": record.get("record_id"), "page": page_number})

    return issues


def build_cross_validation(assignment_manifest: dict[str, Any], report_rows: list[dict[str, Any]]) -> dict[str, Any]:
    vijay_assignments = assignment_manifest.get("assigned_to_vijay", [])
    codex_ready = all(row["status"] == "CERTIFIED" for row in report_rows)
    return {
        "schema": "UNIGURU_VIJAY_CROSS_VALIDATION_REPORT_V1",
        "generated_at": utc_now_iso(),
        "integration_owner": "Vijay",
        "codex_textbooks_ready_for_vijay_review": codex_ready,
        "vijay_assignments_declared": len(vijay_assignments),
        "vijay_assignments": vijay_assignments,
        "cross_validation_required_before_production_merge": True,
        "production_merge_status": "BLOCKED_PENDING_VIJAY_ASSIGNMENTS" if not vijay_assignments else "READY_FOR_CROSS_REVIEW",
        "review_scope": [
            "extraction_quality",
            "evidence_accuracy",
            "lineage",
            "knowledge_graph_relationships",
            "educational_correctness",
            "runtime_compatibility",
        ],
    }


def main() -> None:
    records = load_json(CANONICAL_DATASET)
    manifest = load_json(CANONICAL_MANIFEST)
    authority = load_json(AUTHORITY_REGISTRY)
    pages = load_json(PAGE_REGISTRY)
    ensure_textbook_drop_readme()
    assignment_manifest = ensure_assignment_manifest(authority)

    authorities = {row["textbook_id"]: row for row in authority.get("textbooks", [])}
    pages_by_key = page_lookup(pages)
    rows_by_textbook: dict[str, list[dict[str, Any]]] = defaultdict(list)
    issues_by_textbook: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for record in records:
        textbook_id = str((record.get("evidence") or {}).get("textbook_id"))
        rows_by_textbook[textbook_id].append(record)
        issues_by_textbook[textbook_id].extend(validate_record(record, authorities, pages_by_key))

    report_rows = []
    for textbook_id in sorted(rows_by_textbook):
        record_count = len(rows_by_textbook[textbook_id])
        issues = issues_by_textbook[textbook_id]
        report_rows.append(
            {
                "textbook_id": textbook_id,
                "canonical_record_count": record_count,
                "status": "CERTIFIED" if not issues else "BLOCKED",
                "issue_count": len(issues),
                "issues": issues,
            }
        )

    total_issues = sum(row["issue_count"] for row in report_rows)
    no_new_licensed_downloads = not any(
        row.get("status") == "downloaded_for_this_sprint"
        for row in assignment_manifest.get("assigned_to_codex", [])
    )
    report = {
        "schema": "UNIGURU_PRODUCTION_EXPANSION_REPORT_V1",
        "generated_at": utc_now_iso(),
        "canonical_dataset_path": str(CANONICAL_DATASET.relative_to(ROOT).as_posix()),
        "canonical_dataset_hash": manifest.get("dataset_hash"),
        "canonical_dataset_signature": manifest.get("dataset_signature"),
        "canonical_record_count": len(records),
        "assigned_textbooks_manifest": str(ASSIGNMENT_MANIFEST.relative_to(ROOT).as_posix()),
        "licensed_textbook_drop_root": assignment_manifest.get("licensed_textbook_drop_root"),
        "textbook_rows": report_rows,
        "production_gates": {
            "authority_integrity": total_issues == 0,
            "evidence_integrity": total_issues == 0,
            "provenance_integrity": total_issues == 0,
            "no_synthetic_or_placeholder_records": total_issues == 0,
            "codex_validation_complete": total_issues == 0,
            "vijay_cross_validation_complete": False,
            "new_licensed_downloads_present": not no_new_licensed_downloads,
        },
        "status": "CERTIFIED_CURRENT_CANONICAL_SNAPSHOT" if total_issues == 0 else "BLOCKED",
        "expansion_status": "BLOCKED_PENDING_ASSIGNED_LICENSED_TEXTBOOK_DOWNLOADS" if no_new_licensed_downloads else "READY_FOR_NEW_INGESTION_REVIEW",
        "confidentiality": "No licensed textbook binary content is emitted by this report.",
    }
    report["report_hash"] = stable_hash(report)
    write_json(EXPANSION_REPORT, report)

    cross_validation = build_cross_validation(assignment_manifest, report_rows)
    cross_validation["report_hash"] = stable_hash(cross_validation)
    write_json(CROSS_VALIDATION_REPORT, cross_validation)

    print(
        json.dumps(
            {
                "status": report["status"],
                "expansion_status": report["expansion_status"],
                "canonical_record_count": report["canonical_record_count"],
                "textbook_count": len(report_rows),
                "issue_count": total_issues,
                "vijay_cross_validation": cross_validation["production_merge_status"],
                "report": str(EXPANSION_REPORT.relative_to(ROOT).as_posix()),
                "cross_validation_report": str(CROSS_VALIDATION_REPORT.relative_to(ROOT).as_posix()),
            },
            indent=2,
            ensure_ascii=True,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
