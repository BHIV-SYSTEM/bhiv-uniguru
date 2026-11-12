"""Run a deterministic retrieval-only evaluation against the checked-in Markdown KB."""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from retrieval import retriever as retrieval_module  # noqa: E402
from retrieval.retriever import AdvancedRetriever  # noqa: E402
from integrations.language_adapter import LanguageAdapter  # noqa: E402

DEFAULT_CASES = BACKEND_ROOT / "tests" / "data" / "retrieval_eval_cases.json"
_LANGUAGE_ADAPTER = LanguageAdapter()


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[\w\u0900-\u097f]+", str(value or "").casefold()))


def _evaluate_case(retriever: AdvancedRetriever, case: dict[str, Any], k: int) -> dict[str, Any]:
    start = time.perf_counter()
    retrieval_query = _LANGUAGE_ADAPTER.normalize_query(case["query"]).normalized_query
    results = retriever.retrieve_multi(retrieval_query)
    elapsed_ms = (time.perf_counter() - start) * 1000
    top = results[:k]
    expected_sources = set(case.get("expected_sources", []))
    expected_topics = [_normalize(term) for term in case.get("expected_topics", [])]
    rank = next(
        (position for position, row in enumerate(top, 1) if row.get("path") in expected_sources),
        None,
    )
    hits = {row.get("path") for row in top} & expected_sources
    recall = len(hits) / len(expected_sources) if expected_sources else None
    reciprocal_rank = 1.0 / rank if rank is not None else (0.0 if expected_sources else None)

    relevant_context_docs = 0
    for row in top:
        path = str(row.get("path") or "")
        context = _normalize(f"{path} {row.get('content') or ''}")
        source_match = path in expected_sources
        topic_match = any(term and term in context for term in expected_topics)
        relevant_context_docs += int(source_match or topic_match)
    context_relevance = (
        relevant_context_docs / len(top)
        if top and (expected_sources or expected_topics)
        else (0.0 if not top and (expected_sources or expected_topics) else None)
    )
    return {
        "id": case["id"],
        "category": case["category"],
        "query": case["query"],
        "retrieval_query": retrieval_query,
        "retrieved_sources": [row.get("path") for row in top],
        "source_recall_at_k": recall,
        "first_relevant_rank": rank,
        "reciprocal_rank": reciprocal_rank,
        "context_relevance": context_relevance,
        "latency_ms": round(elapsed_ms, 3),
        "empty_result": not results,
        "max_bm25_score": round(max((row.get("bm25_score", 0.0) for row in results), default=0.0), 6),
        "max_evidence_coverage": round(max((row.get("evidence_coverage", 0.0) for row in results), default=0.0), 6),
    }


def _mean(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [row[field] for row in rows if row[field] is not None]
    return round(statistics.mean(values), 4) if values else None


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [row["latency_ms"] for row in rows]
    supported = [row for row in rows if row["category"] in {"factual", "multi_document", "misspelled", "multilingual"}]
    unsupported = [row for row in rows if row["category"] in {"underspecified_unanswerable", "unrelated"}]
    return {
        "queries": len(rows),
        "source_recall_at_k": _mean(rows, "source_recall_at_k"),
        "mrr": _mean(rows, "reciprocal_rank"),
        "context_relevance": _mean(rows, "context_relevance"),
        "mean_latency_ms": round(statistics.mean(latencies), 3) if latencies else None,
        "empty_results": sum(row["empty_result"] for row in rows),
        "max_bm25_by_label": {
            "supported": {
                "n": len(supported),
                "min": min((row["max_bm25_score"] for row in supported), default=None),
                "median": round(statistics.median(row["max_bm25_score"] for row in supported), 6) if supported else None,
                "max": max((row["max_bm25_score"] for row in supported), default=None),
            },
            "unsupported": {
                "n": len(unsupported),
                "min": min((row["max_bm25_score"] for row in unsupported), default=None),
                "median": round(statistics.median(row["max_bm25_score"] for row in unsupported), 6) if unsupported else None,
                "max": max((row["max_bm25_score"] for row in unsupported), default=None),
            },
        },
        "unsupported_abstention_precision": round(
            sum(row["empty_result"] and row["category"] in {
                "underspecified_unanswerable", "unrelated"
            } for row in rows) / max(1, sum(row["empty_result"] for row in rows)), 4
        ),
        "unsupported_abstention_recall": round(
            sum(row["empty_result"] and row["category"] in {
                "underspecified_unanswerable", "unrelated"
            } for row in rows) / max(1, len(unsupported)), 4
        ),
    }


def run_evaluation(cases_path: Path = DEFAULT_CASES, k: int = 5) -> dict[str, Any]:
    payload = json.loads(cases_path.read_text(encoding="utf-8"))
    cases = payload["cases"]
    knowledge_root = BACKEND_ROOT / "knowledge"
    missing = sorted({
        source for case in cases for source in case.get("expected_sources", [])
        if not (knowledge_root / source).is_file()
    })
    if missing:
        raise ValueError(f"Evaluation references missing KB files: {missing}")
    for case in cases:
        anchored_text = _normalize(" ".join(
            (knowledge_root / source).read_text(encoding="utf-8")
            for source in case.get("expected_sources", [])
        ))
        absent_topics = [
            term for term in case.get("expected_topics", [])
            if _normalize(term) not in anchored_text
        ]
        if absent_topics:
            raise ValueError(f"{case['id']} topic anchors not present in expected KB files: {absent_topics}")

    retriever = AdvancedRetriever()
    # Exclude first-use import/model loading from per-query timing; this is a
    # non-mutating warm-up against the same active corpus.
    if cases:
        retriever.retrieve_multi(cases[0]["query"])
    original_dense_search = retrieval_module._dense_search
    try:
        # The old manifest-gated behavior for the manifestless legacy index was
        # lexical-only. Run that same-corpus reference before the changed path.
        retrieval_module._dense_search = lambda _query, top_k=30: []
        baseline_rows = [_evaluate_case(retriever, case, k) for case in cases]
    finally:
        retrieval_module._dense_search = original_dense_search
    current_rows = [_evaluate_case(retriever, case, k) for case in cases]

    # Current-path queries already attempted dense loading. Do not trigger an
    # extra model/index load solely to report health (which could download weights).
    dense_available = retrieval_module._DENSE_STATE is not None
    baseline = _summarize(baseline_rows)
    current = _summarize(current_rows)
    return {
        "evaluation": "retrieval-only; language-adapter normalization applied; no answer generation or model judging",
        "k": k,
        "corpus": str(knowledge_root),
        "corpus_markdown_files": sum(1 for path in knowledge_root.rglob("*.md") if path.is_file()),
        "case_count": len(cases),
        "dense_index_loaded": dense_available,
        "baseline": {
            "name": "legacy manifest-gated lexical-only reference",
            "summary": baseline,
            "limitations": "Reference emulates the old missing-manifest fallback on the same KB; it is not a full historical checkout replay.",
        },
        "current": {"name": "current language-adapted AdvancedRetriever path", "summary": current},
        "delta_current_minus_baseline": {
            field: round(current[field] - baseline[field], 4)
            if current[field] is not None and baseline[field] is not None else None
            for field in ("source_recall_at_k", "mrr", "context_relevance")
        },
        "answer_correctness": "unavailable: retrieval-only harness; no live generation model configured",
        "faithfulness": "unavailable: no generated answers to judge",
        "cases": current_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("-k", type=int, default=5)
    args = parser.parse_args()
    print(json.dumps(run_evaluation(args.cases, args.k), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
