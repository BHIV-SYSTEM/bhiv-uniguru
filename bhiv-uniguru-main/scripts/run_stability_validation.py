"""
Long-Duration Stability Validation
====================================
Runs 30 queries through the full BHIV ecosystem runtime, measuring:
  - Vijay replay_safe consistency across all runs
  - TANTRA contract stability
  - InsightFlow trace completeness
  - GC and MDU validation stability
  - Execution latency drift (no degradation over time)
  - Zero error rate across all requests

Output: review_packets/proof_logs/stability_report.json
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PROOF_DIR = ROOT / "review_packets" / "proof_logs"

for p in [str(BACKEND), str(ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("UNIGURU_API_AUTH_REQUIRED", "false")

from fastapi.testclient import TestClient
from service.uniguru_runtime_api import app

CLIENT = TestClient(app)

STABILITY_QUERIES = [
    "What is the Bhagavad Gita?",
    "What is karma in Hindu philosophy?",
    "Explain the concept of dharma",
    "What does the Narada Purana say?",
    "Tell me about the Mahabharata",
    "What is the Taittiriya Upanishad?",
    "Who wrote the Puranas?",
    "Explain Ahimsa in ancient texts",
    "What is the Padma Purana?",
    "Describe Vishnu in the Puranas",
    "What is atman in Upanishadic thought?",
    "What is brahman according to the Upanishads?",
    "Explain temple construction in ancient texts",
    "What are the sacred rivers of India?",
    "What is the Narada Bhakti Sutra?",
    "How is renunciation described in the Gita?",
    "Explain karma yoga",
    "What is jnana yoga?",
    "What does the Gita say about moksha?",
    "Describe the role of dharma in kingship",
    "What is the Agni Purana about?",
    "Explain rebirth according to Hindu texts",
    "What is the significance of the Ganga river?",
    "What guidance do ancient texts give on ethics?",
    "Describe the concept of samadhi",
    "What is maya in Upanishadic philosophy?",
    "What is the Bhagavata Purana?",
    "Explain the concept of prana",
    "What does dharma mean for a student?",
    "What is the Katha Upanishad about?",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_stability_validation() -> Dict[str, Any]:
    print(f"Running {len(STABILITY_QUERIES)} stability queries...")
    results: List[Dict[str, Any]] = []
    latencies: List[float] = []
    errors = 0

    for i, query in enumerate(STABILITY_QUERIES, 1):
        started = time.perf_counter()
        try:
            resp = CLIENT.post(
                "/runtime/ecosystem/execute",
                json={"query": query, "emit_proof": False},
            )
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            if resp.status_code == 200:
                body = resp.json()
                vv = body.get("vijay_validation", {})
                tantra = body.get("tantra_contract", {})
                insight = body.get("insightflow_observability", {})
                gc = body.get("gc_validation", {})
                mdu = body.get("mdu_validation", {})
                result = {
                    "run": i,
                    "query_preview": query[:60],
                    "elapsed_ms": elapsed_ms,
                    "status_code": 200,
                    "verification_status": body.get("verification_status"),
                    "vijay_replay_safe": vv.get("replay_safe"),
                    "vijay_hash_chain_ok": vv.get("hash_chain_ok"),
                    "tantra_contract_bound": tantra.get("contract_bound"),
                    "insightflow_trace_complete": insight.get("trace_complete"),
                    "gc_authority_enforced": gc.get("authority_enforced"),
                    "mdu_schema_compatible": mdu.get("schema_compatible"),
                    "error": None,
                }
                latencies.append(elapsed_ms)
            else:
                errors += 1
                result = {
                    "run": i,
                    "query_preview": query[:60],
                    "elapsed_ms": elapsed_ms,
                    "status_code": resp.status_code,
                    "error": f"HTTP {resp.status_code}",
                }
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            errors += 1
            result = {
                "run": i,
                "query_preview": query[:60],
                "elapsed_ms": elapsed_ms,
                "status_code": -1,
                "error": str(exc),
            }
        results.append(result)
        print(f"  [{i:02d}/{len(STABILITY_QUERIES)}] {query[:50]:<50} {result.get('elapsed_ms', 0):.0f}ms  {result.get('verification_status', 'ERR')}")

    # Compute stability metrics
    successful = [r for r in results if r.get("status_code") == 200]
    vijay_safe_all = all(r.get("vijay_replay_safe") is True for r in successful)
    tantra_bound_all = all(r.get("tantra_contract_bound") is True for r in successful)
    insight_complete_all = all(r.get("insightflow_trace_complete") is True for r in successful)
    gc_enforced_all = all(r.get("gc_authority_enforced") is True for r in successful)
    mdu_compat_all = all(r.get("mdu_schema_compatible") is True for r in successful)

    sorted_lat = sorted(latencies)
    n = len(sorted_lat)
    p50 = sorted_lat[int(n * 0.50)] if n else 0
    p95 = sorted_lat[int(n * 0.95)] if n else 0
    p99 = sorted_lat[min(int(n * 0.99), n - 1)] if n else 0

    # Check for latency drift: compare first 10 vs last 10
    first_10 = [r["elapsed_ms"] for r in results[:10] if r.get("elapsed_ms") is not None]
    last_10 = [r["elapsed_ms"] for r in results[-10:] if r.get("elapsed_ms") is not None]
    avg_first = round(sum(first_10) / len(first_10), 2) if first_10 else 0
    avg_last = round(sum(last_10) / len(last_10), 2) if last_10 else 0
    drift_pct = round(abs(avg_last - avg_first) / max(avg_first, 1) * 100, 1)
    no_latency_drift = drift_pct < 30  # <30% drift acceptable

    verdict = "STABLE" if (
        errors == 0
        and vijay_safe_all
        and tantra_bound_all
        and insight_complete_all
        and gc_enforced_all
        and mdu_compat_all
        and no_latency_drift
    ) else "DEGRADED"

    return {
        "schema": "UNIGURU_STABILITY_REPORT_V1",
        "generated_at": _utc_now(),
        "verdict": verdict,
        "total_queries": len(STABILITY_QUERIES),
        "successful": len(successful),
        "errors": errors,
        "stability_checks": {
            "vijay_replay_safe_all_runs": vijay_safe_all,
            "tantra_contract_bound_all_runs": tantra_bound_all,
            "insightflow_trace_complete_all_runs": insight_complete_all,
            "gc_authority_enforced_all_runs": gc_enforced_all,
            "mdu_schema_compatible_all_runs": mdu_compat_all,
            "no_latency_drift": no_latency_drift,
            "zero_errors": errors == 0,
        },
        "latency_stats": {
            "p50_ms": round(p50, 2),
            "p95_ms": round(p95, 2),
            "p99_ms": round(p99, 2),
            "avg_first_10_ms": avg_first,
            "avg_last_10_ms": avg_last,
            "drift_pct": drift_pct,
        },
        "runs": results,
    }


def main() -> None:
    report = run_stability_validation()

    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROOF_DIR / "stability_report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")

    print(f"\nStability Verdict: {report['verdict']}")
    print(f"  Queries: {report['successful']}/{report['total_queries']} successful")
    print(f"  p50={report['latency_stats']['p50_ms']}ms  p95={report['latency_stats']['p95_ms']}ms  drift={report['latency_stats']['drift_pct']}%")
    print(f"Report: {out_path}")


if __name__ == "__main__":
    main()
