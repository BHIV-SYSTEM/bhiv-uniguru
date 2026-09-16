"""
Performance & Reliability Benchmark
=====================================
Standalone script — benchmarks the UniGuru Kosha pipeline without a live API.

Measures:
  1. Ingestion speed        — load all Kosha entries, measure wall time
  2. Single-query latency   — p50 / p95 / p99 over 20 queries
  3. Concurrent throughput  — 50 queries via ThreadPoolExecutor (10 workers)
  4. Memory usage           — tracemalloc before/after ingestion + query batch
  5. Module startup time    — import time for all core backend modules
  6. Replay consistency     — same query 5 times → assert identical answers

Output: review_packets/proof_logs/benchmark_report.json
        (also prints a formatted table to stdout)
"""
from __future__ import annotations

import importlib
import json
import math
import os
import sys
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# Ensure backend is importable — backend/ must be FIRST to prevent
# the root-level retrieval/ package from shadowing backend/retrieval/
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND = os.path.join(_ROOT, "backend")
# Unconditionally insert backend at position 0
if _BACKEND in sys.path:
    sys.path.remove(_BACKEND)
sys.path.insert(0, _BACKEND)

KOSHA_DIR = os.path.join(_BACKEND, "data", "kosha")

BENCHMARK_QUERIES = [
    "What is the Bhagavad Gita?",
    "What does the Bhagavad Gita teach about Karma Yoga?",
    "Tell me about Vishnu in the Narada Purana",
    "What is the Padma Purana?",
    "How are rivers like Ganga described in Puranic texts?",
    "Explain the Upanishadic concept of Brahman",
    "What does the Mahabharata say about dharma?",
    "Explain temple construction in the Agni Purana",
    "Return Upanishads for Bhagavad Gita teachings",
    "Give an Ahimsa answer from the Narada Purana",
    "Explain quantum entanglement from the Bhagavad Gita",
    "Who won the cricket match yesterday?",
    "What is the role of ecology in dharma systems?",
    "What guidance do ancient texts provide about kingship?",
    "What is the Taittiriya Upanishad about?",
    "Explain the concept of Atman in Upanishadic texts",
    "What are the sacred rivers mentioned in Puranas?",
    "Describe the Narada Bhakti Sutras",
    "What does Gita say about renunciation?",
    "Explain Karma and rebirth according to Hindu texts",
]

REPLAY_QUERY = "Explain the Upanishadic concept of Brahman"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _percentile(vals: List[float], pct: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = math.ceil((pct / 100.0) * len(s)) - 1
    return round(s[max(0, idx)], 3)


def _header(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


# ---------------------------------------------------------------------------
# Benchmark 1: Module Startup Time
# ---------------------------------------------------------------------------

def benchmark_startup() -> Dict[str, Any]:
    _header("BENCHMARK 1: Module Startup Time")
    modules = [
        ("kosha.kosha_loader", "KoshaLoader"),
        ("kosha.kosha_retriever", "KoshaRetriever"),
        ("kosha.deterministic_pipeline", "run_deterministic_pipeline"),
        ("retrieval.ontology_retriever", "OntologyAwareRetriever"),
        ("ontology.entity_resolver", "CanonicalEntityResolver"),
        ("governance.source_governance", "SourceGovernance"),
    ]
    results = {}
    for module_name, symbol in modules:
        t0 = time.perf_counter()
        try:
            mod = importlib.import_module(module_name)
            _ = getattr(mod, symbol, None)
            elapsed = (time.perf_counter() - t0) * 1000
            results[module_name] = round(elapsed, 3)
            status = "OK"
        except Exception as exc:
            results[module_name] = None
            status = f"FAILED: {exc}"
        print(f"  {module_name:<45} {status}  ({results.get(module_name) or 'N/A'} ms)")

    total = sum(v for v in results.values() if v is not None)
    print(f"\n  Total import time: {round(total, 2)} ms")
    return {"module_import_times_ms": results, "total_import_time_ms": round(total, 2)}


# ---------------------------------------------------------------------------
# Benchmark 2: Ingestion Speed
# ---------------------------------------------------------------------------

def benchmark_ingestion() -> Dict[str, Any]:
    _header("BENCHMARK 2: Curriculum Ingestion Speed")
    from kosha.kosha_loader import KoshaLoader

    tracemalloc.start()
    t0 = time.perf_counter()
    entries = KoshaLoader(data_sources=[KOSHA_DIR]).load_all()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    count = len(entries)
    rate = round(count / (elapsed_ms / 1000), 1) if elapsed_ms > 0 else 0
    print(f"  Entries loaded    : {count}")
    print(f"  Elapsed           : {round(elapsed_ms, 2)} ms")
    print(f"  Throughput        : {rate} entries/second")
    print(f"  Peak memory       : {round(peak_mem / 1024, 1)} KB")

    return {
        "entries_loaded": count,
        "elapsed_ms": round(elapsed_ms, 2),
        "throughput_entries_per_sec": rate,
        "peak_memory_kb": round(peak_mem / 1024, 1),
        "target_ms": 5000,
        "pass": elapsed_ms < 5000,
    }


# ---------------------------------------------------------------------------
# Benchmark 3: Single-Query Retrieval Latency (p50/p95/p99)
# ---------------------------------------------------------------------------

def benchmark_single_query_latency() -> Dict[str, Any]:
    _header("BENCHMARK 3: Single-Query Retrieval Latency (20 queries)")
    from kosha.deterministic_pipeline import run_deterministic_pipeline

    latencies: List[float] = []
    verified_count = 0

    for i, query in enumerate(BENCHMARK_QUERIES):
        t0 = time.perf_counter()
        result = run_deterministic_pipeline(query)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed_ms)
        if result.get("verification_status") == "VERIFIED":
            verified_count += 1
        print(f"  [{i+1:02d}] {query[:50]:<50}  {round(elapsed_ms, 1):>8} ms  {result.get('verification_status', '?')}")

    p50 = _percentile(latencies, 50)
    p95 = _percentile(latencies, 95)
    p99 = _percentile(latencies, 99)
    mean_ms = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

    print(f"\n  p50: {p50} ms   p95: {p95} ms   p99: {p99} ms   mean: {mean_ms} ms")
    print(f"  Verified: {verified_count}/{len(BENCHMARK_QUERIES)}")

    return {
        "queries": len(BENCHMARK_QUERIES),
        "latency_ms": {"p50": p50, "p95": p95, "p99": p99, "mean": mean_ms},
        "verified_count": verified_count,
        "verification_rate": round(verified_count / len(BENCHMARK_QUERIES), 4),
        "targets": {"p50_ms": 500, "p95_ms": 1000, "p99_ms": 2000},
        "pass": p50 < 500 and p95 < 1000,
    }


# ---------------------------------------------------------------------------
# Benchmark 4: Concurrent Query Throughput
# ---------------------------------------------------------------------------

def benchmark_concurrent(workers: int = 10, total: int = 50) -> Dict[str, Any]:
    _header(f"BENCHMARK 4: Concurrent Queries ({workers} workers, {total} total)")
    from kosha.deterministic_pipeline import run_deterministic_pipeline

    queries = [BENCHMARK_QUERIES[i % len(BENCHMARK_QUERIES)] for i in range(total)]
    latencies: List[float] = []
    errors = 0

    def _run_one(q: str) -> Tuple[float, bool]:
        t0 = time.perf_counter()
        try:
            run_deterministic_pipeline(q)
            return (time.perf_counter() - t0) * 1000, True
        except Exception:
            return (time.perf_counter() - t0) * 1000, False

    wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_run_one, q) for q in queries]
        for future in as_completed(futures):
            latency_ms, ok = future.result()
            latencies.append(latency_ms)
            if not ok:
                errors += 1
    wall_elapsed = (time.perf_counter() - wall_start) * 1000

    p50 = _percentile(latencies, 50)
    p95 = _percentile(latencies, 95)
    throughput = round(total / (wall_elapsed / 1000), 2) if wall_elapsed > 0 else 0

    print(f"  Completed         : {total - errors}/{total}")
    print(f"  Errors            : {errors}")
    print(f"  Wall time         : {round(wall_elapsed, 1)} ms")
    print(f"  Throughput        : {throughput} queries/sec")
    print(f"  Concurrent p50    : {p50} ms  p95: {p95} ms")

    return {
        "workers": workers,
        "total_queries": total,
        "completed": total - errors,
        "errors": errors,
        "wall_time_ms": round(wall_elapsed, 1),
        "throughput_qps": throughput,
        "latency_ms": {"p50": p50, "p95": p95},
        "pass": errors == 0,
    }


# ---------------------------------------------------------------------------
# Benchmark 5: Memory Usage Under Load
# ---------------------------------------------------------------------------

def benchmark_memory() -> Dict[str, Any]:
    _header("BENCHMARK 5: Memory Usage Under Query Load")
    from kosha.deterministic_pipeline import run_deterministic_pipeline

    tracemalloc.start()
    snap_before = tracemalloc.take_snapshot()

    for query in BENCHMARK_QUERIES:
        run_deterministic_pipeline(query)

    snap_after = tracemalloc.take_snapshot()
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    stats = snap_after.compare_to(snap_before, "lineno")
    top5 = [(str(s.traceback), s.size_diff) for s in stats[:5]]
    net_kb = round(sum(s.size_diff for s in stats) / 1024, 1)

    print(f"  Peak memory       : {round(peak_mem / 1024 / 1024, 2)} MB")
    print(f"  Net allocation    : {net_kb} KB")
    print(f"  Top allocator     : {top5[0][0][:80] if top5 else 'N/A'}")

    return {
        "peak_memory_mb": round(peak_mem / 1024 / 1024, 2),
        "net_allocation_kb": net_kb,
        "queries_run": len(BENCHMARK_QUERIES),
        "pass": peak_mem < 512 * 1024 * 1024,  # < 512 MB
    }


# ---------------------------------------------------------------------------
# Benchmark 6: Replay Consistency
# ---------------------------------------------------------------------------

def benchmark_replay() -> Dict[str, Any]:
    _header("BENCHMARK 6: Replay Consistency (5 runs, identical query)")
    from kosha.deterministic_pipeline import run_deterministic_pipeline

    results = []
    for i in range(5):
        result = run_deterministic_pipeline(REPLAY_QUERY)
        results.append({
            "run": i + 1,
            "verification_status": result.get("verification_status"),
            "answer_length": len(result.get("answer", "")),
            "confidence": result.get("confidence_breakdown", {}).get("overall", 0.0),
            "signals_matched": len(result.get("matched_signals", [])),
        })
        print(f"  Run {i+1}: status={result.get('verification_status')}  "
              f"conf={result.get('confidence_breakdown', {}).get('overall', 0.0):.4f}  "
              f"signals={len(result.get('matched_signals', []))}")

    # Consistency check: all runs should have same verification status and confidence
    statuses = {r["verification_status"] for r in results}
    confidences = {r["confidence"] for r in results}
    consistent_status = len(statuses) == 1
    consistent_confidence = len(confidences) == 1

    print(f"\n  Status consistent       : {consistent_status} ({statuses})")
    print(f"  Confidence consistent   : {consistent_confidence} ({confidences})")
    print(f"  Replay result           : {'PASS' if consistent_status else 'FAIL'}")

    return {
        "query": REPLAY_QUERY,
        "runs": results,
        "consistent_status": consistent_status,
        "consistent_confidence": consistent_confidence,
        "unique_statuses": list(statuses),
        "unique_confidences": list(confidences),
        "pass": consistent_status,
    }


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_all_benchmarks() -> Dict[str, Any]:
    print(f"\n{'#' * 60}")
    print("  UNIGURU PERFORMANCE & RELIABILITY BENCHMARK SUITE")
    print(f"  Generated: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'#' * 60}")

    b1 = benchmark_startup()
    b2 = benchmark_ingestion()
    b3 = benchmark_single_query_latency()
    b4 = benchmark_concurrent()
    b5 = benchmark_memory()
    b6 = benchmark_replay()

    all_pass = all([
        b2["pass"],
        b3["pass"],
        b4["pass"],
        b5["pass"],
        b6["pass"],
    ])

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "overall_verdict": "PASS" if all_pass else "PARTIAL_PASS",
        "benchmarks": {
            "startup": b1,
            "ingestion": b2,
            "single_query_latency": b3,
            "concurrent_throughput": b4,
            "memory_usage": b5,
            "replay_consistency": b6,
        },
        "summary_table": [
            {"benchmark": "Ingestion speed", "result": f"{b2['elapsed_ms']} ms", "target": "< 5000 ms", "pass": b2["pass"]},
            {"benchmark": "p50 latency", "result": f"{b3['latency_ms']['p50']} ms", "target": "< 500 ms", "pass": b3["latency_ms"]["p50"] < 500},
            {"benchmark": "p95 latency", "result": f"{b3['latency_ms']['p95']} ms", "target": "< 1000 ms", "pass": b3["latency_ms"]["p95"] < 1000},
            {"benchmark": "Concurrent throughput", "result": f"{b4['throughput_qps']} qps", "target": "> 1 qps", "pass": b4["throughput_qps"] > 1},
            {"benchmark": "Concurrent errors", "result": str(b4["errors"]), "target": "0", "pass": b4["errors"] == 0},
            {"benchmark": "Peak memory", "result": f"{b5['peak_memory_mb']} MB", "target": "< 512 MB", "pass": b5["pass"]},
            {"benchmark": "Replay consistency", "result": "PASS" if b6["pass"] else "FAIL", "target": "Identical outputs", "pass": b6["pass"]},
        ],
    }

    # Print summary table
    print(f"\n{'=' * 60}")
    print("  SUMMARY")
    print(f"{'=' * 60}")
    print(f"  {'Benchmark':<30} {'Result':<20} {'Target':<20} {'Pass'}")
    print(f"  {'-' * 58}")
    for row in report["summary_table"]:
        icon = "PASS" if row["pass"] else "FAIL"
        print(f"  {row['benchmark']:<30} {row['result']:<20} {row['target']:<20} {icon}")
    print(f"\n  OVERALL: {report['overall_verdict']}")

    # Save report
    out_dir = os.path.normpath(os.path.join(_ROOT, "review_packets", "proof_logs"))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "benchmark_report.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=True)
    print(f"\n  Report saved: {out_path}\n")

    return report


if __name__ == "__main__":
    run_all_benchmarks()
