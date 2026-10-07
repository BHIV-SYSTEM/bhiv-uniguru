"""
UniGuru 100-Question Multi-Capability Evaluation Runner
======================================================
Executes the comprehensive 100-question test suite across all capabilities:
  - Conversation & Identity
  - Multi-Turn Session Memory & Follow-ups
  - Mathematics (Symbolic & Numerical)
  - Physics (Mechanics, Forces, Formulas)
  - Chemistry & Biology
  - Programming & SQL
  - English & Translation
  - UniGuru Knowledge Base & RAG
  - General Knowledge & Current Info
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Fix console encoding on Windows
if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr is not None and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure offline mode for sentence_transformers
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from service.universal_orchestrator import get_universal_orchestrator


def run_evaluation() -> bool:
    dataset_path = ROOT_DIR / "tests" / "evaluation_100_dataset.json"
    if not dataset_path.exists():
        print(f"[FAIL] Evaluation dataset not found at {dataset_path}")
        return False

    with dataset_path.open("r", encoding="utf-8") as f:
        dataset = json.load(f)

    print("=" * 80)
    print(f"RUNNING UNIGURU MULTI-CAPABILITY 100-QUESTION BENCHMARK ({len(dataset)} QUERIES)")
    print("=" * 80)

    orchestrator = get_universal_orchestrator()

    total = len(dataset)
    passed = 0
    failed = 0
    category_stats = {}

    results = []

    # Maintain continuous session for follow-up testing
    session_id = "eval_benchmark_session_01"

    for item in dataset:
        q_id = item["id"]
        question = item["question"]
        exp_cap = item["expected_capability"]
        exp_snippet = item["expected_snippet"]

        t0 = time.perf_counter()
        res = orchestrator.process_query(
            query=question,
            session_id=session_id,
            user_id="test_runner",
        )
        latency = (time.perf_counter() - t0) * 1000

        actual_cap = res.get("category")
        answer = res.get("answer", "")

        # Check pass criteria
        # 1. Answer is non-empty
        # 2. Answer contains expected snippet (case-insensitive)
        snippet_match = exp_snippet.lower() in answer.lower()
        # For certain categories, capability or intent alignment
        is_pass = bool(answer and snippet_match)

        if is_pass:
            passed += 1
            status_str = "[PASS]"
        else:
            failed += 1
            status_str = "[FAIL]"

        cat_entry = category_stats.setdefault(exp_cap, {"total": 0, "passed": 0})
        cat_entry["total"] += 1
        if is_pass:
            cat_entry["passed"] += 1

        results.append({
            "id": q_id,
            "question": question,
            "expected_capability": exp_cap,
            "actual_capability": actual_cap,
            "expected_snippet": exp_snippet,
            "actual_answer": answer[:150] + ("..." if len(answer) > 150 else ""),
            "latency_ms": round(latency, 2),
            "status": "PASS" if is_pass else "FAIL",
        })

        if q_id % 10 == 0 or not is_pass:
            print(f"{status_str} #{q_id:03d} | [{exp_cap:18s}] | Q: {question[:35]:35s} | Latency: {latency:6.1f}ms")

    print("\n" + "=" * 80)
    print("CATEGORY BREAKDOWN & ACCURACY:")
    print("=" * 80)
    for cat, stat in sorted(category_stats.items()):
        p = stat["passed"]
        tot = stat["total"]
        pct = (p / tot) * 100 if tot else 0
        print(f"  {cat:22s}: {p:2d} / {tot:2d} ({pct:5.1f}%)")

    pass_rate = (passed / total) * 100
    print("=" * 80)
    print(f"TOTAL EVALUATION RESULT: {passed}/{total} Passed ({pass_rate:.1f}%)")
    print("=" * 80)

    # Save detailed evaluation report
    report_path = ROOT_DIR / "tests" / "evaluation_100_results.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.time(),
            "total_queries": total,
            "passed": passed,
            "failed": failed,
            "pass_rate_pct": round(pass_rate, 2),
            "category_breakdown": category_stats,
            "details": results,
        }, f, indent=2, ensure_ascii=False)
    print(f"Detailed results written to {report_path}")

    return passed == total


if __name__ == "__main__":
    success = run_evaluation()
    sys.exit(0 if success else 1)
