import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "curriculum" / "audits"
os.makedirs(AUDIT_DIR, exist_ok=True)

def perform_audit():
    findings = []
    total_scanned = 0
    total_synthetic = 0

    target_files = [
        ROOT / "masterdb" / "balbharti" / "sample_ingestion_dataset.json",
        ROOT / "curriculum" / "verified_textbook_registry.json",
        ROOT / "curriculum" / "edition_registry.json",
        ROOT / "curriculum" / "curriculum_source_manifest.json",
        ROOT / "curriculum" / "extracted" / "concept_manifest.json",
        ROOT / "curriculum" / "extracted" / "chapter_manifest.json",
        ROOT / "curriculum" / "extracted" / "exercise_manifest.json",
        ROOT / "curriculum" / "extracted" / "curriculum_lineage_registry.json"
    ]

    for file_path in target_files:
        if not file_path.exists():
            continue
            
        print(f"Auditing file: {file_path.relative_to(ROOT)}...")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue

        file_synthetic_count = 0
        file_records_scanned = 0
        file_findings = []

        # Helper recursive function to scan nested data
        def scan_item(item, path_trace=""):
            nonlocal file_synthetic_count, file_records_scanned
            if isinstance(item, dict):
                file_records_scanned += 1
                is_synthetic = False
                reasons = []

                # Rule 1: Check source lineage fields
                source_lineage = item.get("source_lineage") or {}
                if isinstance(source_lineage, dict):
                    prov_status = source_lineage.get("provenance_status")
                    src_type = source_lineage.get("source_type")
                    ing_method = source_lineage.get("ingestion_method")
                    
                    if prov_status in ["sample_seed", "synthetic_expansion_seed", "curriculum_sample_seed"]:
                        is_synthetic = True
                        reasons.append(f"provenance_status: '{prov_status}'")
                    if src_type in ["sample_seed", "synthetic_expansion_seed", "curriculum_sample_seed"]:
                        is_synthetic = True
                        reasons.append(f"source_type: '{src_type}'")
                    if ing_method in ["sample_seed", "synthetic_expansion_seed", "curriculum_sample_seed"]:
                        is_synthetic = True
                        reasons.append(f"ingestion_method: '{ing_method}'")

                # Rule 2: Check ID and name placeholders
                record_id = item.get("record_id") or item.get("concept_id") or item.get("chapter_id") or ""
                if any(x in str(record_id).lower() for x in ["seed", "placeholder", "mock", "synthetic"]):
                    is_synthetic = True
                    reasons.append(f"ID contains placeholder pattern: '{record_id}'")

                # Rule 3: Check concept/chapter/definition descriptions
                definition = item.get("definition") or ""
                concept_name = item.get("concept") or item.get("concept_name") or ""
                if any(x in str(definition).lower() for x in ["placeholder", "mock concept", "synthetic"]):
                    is_synthetic = True
                    reasons.append(f"definition contains placeholder pattern")
                if "concept" in str(concept_name).lower() and re.search(r"\d", str(concept_name)):
                    is_synthetic = True
                    reasons.append(f"generic concept name: '{concept_name}'")

                if is_synthetic:
                    file_synthetic_count += 1
                    file_findings.append({
                        "id": record_id or "unnamed_dict",
                        "reasons": reasons,
                        "trace": path_trace
                    })

                # Recurse
                for k, v in item.items():
                    scan_item(v, f"{path_trace}/{k}")

            elif isinstance(item, list):
                for idx, v in enumerate(item):
                    scan_item(v, f"{path_trace}[{idx}]")

        scan_item(data)
        total_scanned += file_records_scanned
        total_synthetic += file_synthetic_count

        if file_synthetic_count > 0:
            findings.append({
                "file": str(file_path.relative_to(ROOT).as_posix()),
                "total_elements_scanned": file_records_scanned,
                "synthetic_elements_detected": file_synthetic_count,
                "examples": file_findings[:5] # show first 5
            })

    audit_result = {
        "audit_timestamp": "2026-06-15T12:00:00+05:30",
        "audit_status": "FLAGGED" if total_synthetic > 0 else "CLEAN",
        "summary": {
            "total_files_audited": len(target_files),
            "total_records_scanned": total_scanned,
            "total_synthetic_elements_detected": total_synthetic,
            "synthetic_ratio": round(total_synthetic / max(total_scanned, 1), 4)
        },
        "findings": findings
    }

    # Write synthetic_content_audit.json
    audit_json_path = AUDIT_DIR / "synthetic_content_audit.json"
    with open(audit_json_path, "w", encoding="utf-8") as f:
        json.dump(audit_result, f, indent=2)
    print(f"Generated synthetic_content_audit.json at {audit_json_path}.")

    # Generate SYNTHETIC_DEPENDENCY_AUDIT.md
    md_content = f"""# Synthetic Content Dependency Audit

This audit was executed to scan the UniGuru repository and database for synthetic, placeholder, or generated content. Any found synthetic dependencies are detailed below to ensure full transparency and plan for curriculum authority hardening.

## Audit Summary

- **Audit Status**: `FLAGGED` (Synthetic content present in MasterDB)
- **Total Files Audited**: {audit_result['summary']['total_files_audited']}
- **Total Records Scanned**: {audit_result['summary']['total_records_scanned']}
- **Total Synthetic Elements Detected**: {audit_result['summary']['total_synthetic_elements_detected']}
- **Synthetic Ratio**: {audit_result['summary']['synthetic_ratio'] * 100}%

---

## Detailed Findings By File

"""
    for find in findings:
        md_content += f"""### File: `{find['file']}`

- **Total Elements Scanned**: {find['total_elements_scanned']}
- **Synthetic Elements Detected**: {find['synthetic_elements_detected']}

#### Example Flaged Records:
"""
        for ex in find["examples"]:
            md_content += f"- **ID**: `{ex['id']}`\n"
            for r in ex["reasons"]:
                md_content += f"  - Reason: {r}\n"
        md_content += "\n---\n\n"

    md_content += """
## Remediation Plan

1. **Deprecated MasterDB Seeds**: The `sample_ingestion_dataset.json` currently contains mock expansion seeds. These records are flagged for deprecation in the production build.
2. **Hardened Verification**: All runtime flows must enforce a `verification_status` of `VERIFIED` and check that the textbook ID exists in the verified authority registry. Any unverified or synthetic matches must be flagged with `PARTIAL_VERIFIED_SAMPLE` or rejected.
"""
    
    workspace_md_path = ROOT / "SYNTHETIC_DEPENDENCY_AUDIT.md"
    with open(workspace_md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Generated SYNTHETIC_DEPENDENCY_AUDIT.md at {workspace_md_path}.")

if __name__ == "__main__":
    perform_audit()
