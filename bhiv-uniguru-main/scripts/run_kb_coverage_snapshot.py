from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KB_ROOT = ROOT / "backend" / "uniguru" / "knowledge"
OUTPUT_JSON = ROOT / "demo_logs" / "kb_coverage_snapshot.json"
OUTPUT_MD = ROOT / "docs" / "reports" / "KB_COVERAGE_SUMMARY.md"


def main() -> None:
    if not KB_ROOT.exists():
        data = {"kb_root": str(KB_ROOT), "exists": False, "markdown_files": 0, "domains": {}}
        OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return

    md_files = list(KB_ROOT.rglob("*.md"))
    domain_counter: Counter[str] = Counter()
    for path in md_files:
        rel = path.relative_to(KB_ROOT).parts
        domain = rel[0] if rel else "unknown"
        domain_counter[domain] += 1

    data = {
        "kb_root": str(KB_ROOT),
        "exists": True,
        "markdown_files": len(md_files),
        "domains": dict(sorted(domain_counter.items(), key=lambda kv: kv[0])),
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")

    lines = [
        "# KB Coverage Summary",
        "",
        f"- KB root: `{KB_ROOT.as_posix()}`",
        f"- Markdown files: `{len(md_files)}`",
        "",
        "## Domain Distribution",
    ]
    for domain, count in sorted(domain_counter.items(), key=lambda kv: kv[0]):
        lines.append(f"- `{domain}`: {count}")
    lines.extend(
        [
            "",
            "## Artifacts",
            f"- JSON: `{OUTPUT_JSON.as_posix()}`",
            f"- This report: `{OUTPUT_MD.as_posix()}`",
        ]
    )
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(str(OUTPUT_JSON))


if __name__ == "__main__":
    main()
