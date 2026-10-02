from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learning_runtime.learning_intelligence import build_learning_intelligence
from backend.memory.constitutional_semantic_memory import utc_now_iso
from retrieval.retrieval_engine import (
    build_curriculum_graph,
    generate_retrieval_artifact,
    load_masterdb_records,
    retrieve_from_masterdb,
)

CURRICULUM_GRAPH_PATH = ROOT / "retrieval" / "curriculum_graph.json"
RETRIEVAL_ARTIFACT_PATH = ROOT / "retrieval" / "retrieval_artifact.json"
QUALITY_REPORT_PATH = ROOT / "review_packets" / "proof_logs" / "retrieval_quality_report.json"
LEARNING_DEMO_PATH = ROOT / "review_packets" / "proof_logs" / "learning_intelligence_demo.json"

SAMPLE_QUERIES = [
    {"query": "Grade 2 Marathi Medium: how do numbers help us count objects?", "grade": 2, "medium": "Marathi Medium", "subject": "Mathematics"},
    {"query": "Grade 5 History: what can we learn from early people?", "grade": 5, "medium": "English Medium", "subject": "History"},
    {"query": "Grade 7 Geography: how do maps help us understand places?", "grade": 7, "medium": "English Medium", "subject": "Geography"},
    {"query": "Grade 10 Science: explain force and motion with an example.", "grade": 10, "medium": "English Medium", "subject": "Science"},
    {"query": "Grade 8 English: how should I identify the main idea in a story?", "grade": 8, "medium": "English Medium", "subject": "English"},
]


def main() -> None:
    records = load_masterdb_records()
    graph = build_curriculum_graph(records)
    CURRICULUM_GRAPH_PATH.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")

    artifacts: List[Dict[str, Any]] = []
    quality_rows: List[Dict[str, Any]] = []
    for scenario in SAMPLE_QUERIES:
        retrieval = retrieve_from_masterdb(
            scenario["query"],
            grade=scenario.get("grade"),
            medium=scenario.get("medium"),
            subject=scenario.get("subject"),
        )
        artifact = generate_retrieval_artifact(
            scenario["query"],
            grade=scenario.get("grade"),
            medium=scenario.get("medium"),
            subject=scenario.get("subject"),
        )
        learning = build_learning_intelligence(scenario["query"], retrieval)
        artifacts.append(
            {
                "scenario": scenario,
                "retrieval": retrieval,
                "artifact": artifact,
                "learning_state": learning,
            }
        )
        quality_rows.append(
            {
                "query": scenario["query"],
                "grade": scenario.get("grade"),
                "medium": scenario.get("medium"),
                "subject": scenario.get("subject"),
                "confidence": retrieval.get("confidence", 0.0),
                "matched_record_id": (retrieval.get("best_record") or {}).get("record_id"),
                "matched_concept": (retrieval.get("best_record") or {}).get("concept"),
            }
        )

    RETRIEVAL_ARTIFACT_PATH.write_text(json.dumps(artifacts[0]["artifact"], indent=2, ensure_ascii=False), encoding="utf-8")

    quality_report = {
        "schema": "UNIGURU_RETRIEVAL_QUALITY_REPORT_V1",
        "generated_at": utc_now_iso(),
        "query_count": len(quality_rows),
        "average_confidence": round(sum(row["confidence"] for row in quality_rows) / max(len(quality_rows), 1), 4),
        "rows": quality_rows,
    }
    QUALITY_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUALITY_REPORT_PATH.write_text(json.dumps(quality_report, indent=2, ensure_ascii=False), encoding="utf-8")
    LEARNING_DEMO_PATH.write_text(json.dumps(artifacts, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote curriculum graph to {CURRICULUM_GRAPH_PATH}")
    print(f"Wrote retrieval artifact to {RETRIEVAL_ARTIFACT_PATH}")
    print(f"Wrote retrieval quality report to {QUALITY_REPORT_PATH}")
    print(f"Wrote learning demo to {LEARNING_DEMO_PATH}")


if __name__ == "__main__":
    main()
