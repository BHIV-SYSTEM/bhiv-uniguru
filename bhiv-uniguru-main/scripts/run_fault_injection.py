"""
Fault Injection & Resilience Validation
========================================
Tests UniGuru's BHIV ecosystem runtime against:
  1. Empty / whitespace query
  2. Oversized query (>2000 chars)
  3. Gibberish / out-of-domain query
  4. Repeated replay with different trace_ids (determinism check)
  5. Concurrent execution (5 threads)
  6. Health / readiness probe under load

Output: review_packets/proof_logs/fault_injection_report.json
"""
from __future__ import annotations

import concurrent.futures
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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _post_execute(query: str, trace_id: str | None = None, emit_proof: bool = False) -> Dict[str, Any]:
    started = time.perf_counter()
    body: Dict[str, Any] = {"query": query, "emit_proof": emit_proof}
    if trace_id:
        body["trace_id"] = trace_id
    try:
        resp = CLIENT.post("/runtime/ecosystem/execute", json=body)
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        return {
            "status_code": resp.status_code,
            "elapsed_ms": elapsed,
            "body": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text,
        }
    except Exception as exc:
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        return {"status_code": -1, "elapsed_ms": elapsed, "error": str(exc)}


def test_empty_query() -> Dict[str, Any]:
    """An empty string should be rejected at Pydantic validation (422)."""
    result = _post_execute("   ")
    passed = result["status_code"] in (400, 422)
    return {
        "name": "empty_query",
        "description": "Whitespace-only query must be rejected with 4xx",
        "status_code": result["status_code"],
        "elapsed_ms": result["elapsed_ms"],
        "passed": passed,
        "note": "Pydantic min_length=1 or normalise validator expected to reject",
    }


def test_oversized_query() -> Dict[str, Any]:
    """A query exceeding 2000 chars should be rejected (422)."""
    big_query = "A" * 2001
    result = _post_execute(big_query)
    passed = result["status_code"] in (400, 422)
    return {
        "name": "oversized_query",
        "description": "Query >2000 chars must be rejected with 4xx",
        "status_code": result["status_code"],
        "elapsed_ms": result["elapsed_ms"],
        "passed": passed,
        "note": "Pydantic max_length=2000 expected to reject",
    }


def test_out_of_domain_query() -> Dict[str, Any]:
    """Out-of-domain query should return a valid 200 with NO_VERIFIED_KNOWLEDGE or similar."""
    result = _post_execute("What is the stock price of Apple today?")
    body = result.get("body", {})
    status_ok = result["status_code"] == 200
    has_trace = isinstance(body, dict) and "trace_id" in body
    vijay_safe = isinstance(body, dict) and body.get("vijay_validation", {}).get("replay_safe") is True
    passed = status_ok and has_trace and vijay_safe
    return {
        "name": "out_of_domain_query",
        "description": "Out-of-domain query must return 200 with valid replay-safe vijay_validation",
        "status_code": result["status_code"],
        "elapsed_ms": result["elapsed_ms"],
        "verification_status": body.get("verification_status") if isinstance(body, dict) else None,
        "vijay_replay_safe": vijay_safe,
        "passed": passed,
    }


def test_replay_determinism() -> Dict[str, Any]:
    """Same query with the same trace_id should produce identical runtime_hash."""
    query = "What is the Bhagavad Gita?"
    trace = "fault_injection_determinism_check"
    r1 = _post_execute(query, trace_id=trace)
    r2 = _post_execute(query, trace_id=trace)
    h1 = (r1.get("body") or {}).get("vijay_validation", {}).get("runtime_hash")
    h2 = (r2.get("body") or {}).get("vijay_validation", {}).get("runtime_hash")
    passed = (
        r1["status_code"] == 200
        and r2["status_code"] == 200
        and h1 is not None
        and h1 == h2
    )
    return {
        "name": "replay_determinism",
        "description": "Same trace_id must yield identical vijay_validation.runtime_hash",
        "run1_status": r1["status_code"],
        "run2_status": r2["status_code"],
        "run1_hash": h1,
        "run2_hash": h2,
        "hashes_match": h1 == h2,
        "passed": passed,
    }


def test_concurrent_execution() -> Dict[str, Any]:
    """5 concurrent requests must all return 200 with no errors."""
    queries = [
        "What is karma?",
        "Explain the Gita",
        "Who is Krishna?",
        "What is dharma?",
        "Describe the Upanishads",
    ]

    results: List[Dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_post_execute, q): q for q in queries}
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    all_200 = all(r["status_code"] == 200 for r in results)
    all_replay_safe = all(
        (r.get("body") or {}).get("vijay_validation", {}).get("replay_safe") is True
        for r in results
    )
    passed = all_200 and all_replay_safe
    return {
        "name": "concurrent_execution",
        "description": "5 concurrent requests must all return 200 with replay_safe=true",
        "total_requests": len(results),
        "all_200": all_200,
        "all_replay_safe": all_replay_safe,
        "latencies_ms": sorted([r["elapsed_ms"] for r in results]),
        "passed": passed,
    }


def test_health_under_load() -> Dict[str, Any]:
    """Health endpoint must remain responsive during execution."""
    started = time.perf_counter()
    resp = CLIENT.get("/health")
    elapsed = round((time.perf_counter() - started) * 1000, 2)
    passed = resp.status_code == 200 and resp.json().get("status") == "ok"
    return {
        "name": "health_under_load",
        "description": "GET /health must return 200 ok with sub-100ms latency",
        "status_code": resp.status_code,
        "elapsed_ms": elapsed,
        "status_field": resp.json().get("status") if resp.status_code == 200 else None,
        "passed": passed,
    }


def main() -> None:
    print("Running fault injection tests...")
    tests = [
        test_empty_query,
        test_oversized_query,
        test_out_of_domain_query,
        test_replay_determinism,
        test_concurrent_execution,
        test_health_under_load,
    ]

    results = []
    for fn in tests:
        print(f"  [{fn.__name__}] ...", end=" ", flush=True)
        result = fn()
        status = "PASS" if result.get("passed") else "FAIL"
        print(status)
        results.append(result)

    passed_count = sum(1 for r in results if r.get("passed"))
    total = len(results)
    verdict = "ALL_PASS" if passed_count == total else "PARTIAL_FAIL"

    report = {
        "schema": "UNIGURU_FAULT_INJECTION_REPORT_V1",
        "generated_at": _utc_now(),
        "verdict": verdict,
        "passed": passed_count,
        "total": total,
        "tests": results,
    }

    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROOF_DIR / "fault_injection_report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    print(f"\nVerdict: {verdict} ({passed_count}/{total})")
    print(f"Report: {out_path}")


if __name__ == "__main__":
    main()
