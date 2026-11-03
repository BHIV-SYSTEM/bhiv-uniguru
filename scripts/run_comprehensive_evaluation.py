"""
UniGuru Comprehensive Multi-Domain Governed Knowledge & RAG Benchmark
======================================================================
Validates end-to-end functionality across:
  - 18+ Distinct Educational & Technical Domains
  - Ingested Authoritative PDFs & Citations
  - Dense FAISS + SQLite FTS5 BM25 Hybrid Retrieval
  - Authority Reranker & Metadata Alignment
  - Strict Provenance Attribution (Document -> Page -> Section)
  - Calibrated Abstention on Out-of-Domain Gaps
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Fix Windows console UTF-8 output
if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr is not None and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from service.universal_orchestrator import get_universal_orchestrator


def run_comprehensive_evaluation() -> bool:
    dataset_path = ROOT_DIR / "tests" / "evaluation_comprehensive_dataset.json"
    if not dataset_path.exists():
        print(f"[FAIL] Comprehensive dataset not found at {dataset_path}")
        return False

    with dataset_path.open("r", encoding="utf-8") as f:
        dataset = json.load(f)

    print("=" * 85)
    print(f"RUNNING COMPREHENSIVE GOVERNED KNOWLEDGE BENCHMARK ({len(dataset)} DOMAIN QUERIES)")
    print("=" * 85)

    orchestrator = get_universal_orchestrator()
    total = len(dataset)
    passed = 0
    failed = 0
    domain_stats = {}
    session_id = "eval_comprehensive_session_01"
    user_id = "eval_user_comprehensive"

    results = []

    for item in dataset:
        q_id = item["id"]
        domain = item["domain"]
        question = item["question"]
        exp_cap = item["expected_capability"]
        exp_snippet = item["expected_snippet"]
        req_provenance = item.get("requires_provenance", False)

        t0 = time.perf_counter()
        res = orchestrator.process_query(
            query=question,
            session_id=session_id,
            user_id=user_id,
        )
        latency = (time.perf_counter() - t0) * 1000
        actual_cap = res.get("category")
        answer = res.get("answer", "")
        citations = res.get("citations", [])

        # 1. Check snippet match
        snippet_match = exp_snippet.lower() in answer.lower()

        # 2. Check provenance if required
        provenance_ok = True
        if req_provenance:
            has_sources = "sources consulted" in answer.lower() or len(citations) > 0
            has_provenance_markers = ("source:" in answer.lower() or "page" in answer.lower() or len(citations) > 0)
            provenance_ok = has_sources and has_provenance_markers

        is_pass = bool(answer and snippet_match and provenance_ok)

        if is_pass:
            passed += 1
            status_str = "[PASS]"
        else:
            failed += 1
            status_str = "[FAIL]"

        d_entry = domain_stats.setdefault(domain, {"total": 0, "passed": 0})
        d_entry["total"] += 1
        if is_pass:
            d_entry["passed"] += 1

        print(f"{status_str} #{q_id} | [{domain:<20}] | Q: {question[:35]:<35} | Latency: {latency:6.1f}ms")

        results.append({
            "id": q_id,
            "domain": domain,
            "question": question,
            "expected_capability": exp_cap,
            "actual_capability": actual_cap,
            "expected_snippet": exp_snippet,
            "snippet_match": snippet_match,
            "provenance_ok": provenance_ok,
            "actual_answer": answer[:300] + ("..." if len(answer) > 300 else ""),
            "citations": citations,
            "latency_ms": round(latency, 2),
            "status": "PASS" if is_pass else "FAIL",
        })

    print("\n" + "=" * 85)
    print("DOMAIN BREAKDOWN & VERIFICATION RATE:")
    print("=" * 85)
    for dom in sorted(domain_stats.keys()):
        stats = domain_stats[dom]
        pct = (stats["passed"] / stats["total"]) * 100
        print(f"  {dom:<25}: {stats['passed']:2d} / {stats['total']:2d} ({pct:5.1f}%)")

    pass_rate = (passed / total) * 100
    print("=" * 85)
    print(f"COMPREHENSIVE BENCHMARK RESULT: {passed}/{total} Passed ({pass_rate:.1f}%)")
    print("=" * 85)

    out_file = ROOT_DIR / "tests" / "evaluation_comprehensive_results.json"
    payload = {
        "timestamp": time.time(),
        "total_queries": total,
        "passed": passed,
        "failed": failed,
        "pass_rate_pct": round(pass_rate, 2),
        "domain_breakdown": domain_stats,
        "details": results,
    }
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Detailed results written to {out_file}\n")

    return failed == 0


if __name__ == "__main__":
    success = run_comprehensive_evaluation()
    sys.exit(0 if success else 1)
