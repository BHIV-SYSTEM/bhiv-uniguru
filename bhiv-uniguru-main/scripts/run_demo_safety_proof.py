from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests


ROOT = Path(__file__).resolve().parents[1]
PYTHON_PORT = int(os.getenv("UNIGURU_PYTHON_PORT", "8000"))
NODE_PORT = int(os.getenv("UNIGURU_NODE_PORT", "8080"))
PYTHON_BASE = f"http://127.0.0.1:{PYTHON_PORT}"
NODE_BASE = f"http://127.0.0.1:{NODE_PORT}"
OUTPUT_JSON = ROOT / "demo_logs" / "demo_safety_proof.json"
OUTPUT_MD = ROOT / "docs" / "reports" / "DEMO_STABILITY_PROOF.md"
KNOWLEDGE_DIR = ROOT / "backend" / "uniguru" / "knowledge"
KNOWLEDGE_BACKUP = ROOT / "backend" / "uniguru" / "knowledge.__demo_backup"
SAFE_PREFIX = "I am still learning this topic, but here is a basic explanation..."


def _wait_for_health(url: str, timeout_seconds: int = 40) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"Service did not become healthy in time: {url}")


def _stop(proc: subprocess.Popen[Any]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def _start_stack(env_overrides: Dict[str, str]) -> tuple[subprocess.Popen[Any], subprocess.Popen[Any]]:
    env_backend = os.environ.copy()
    env_backend["PYTHONPATH"] = str(ROOT / "backend")
    env_backend["UNIGURU_HOST"] = "127.0.0.1"
    env_backend["UNIGURU_PORT"] = str(PYTHON_PORT)
    env_backend["NODE_BACKEND_PORT"] = str(NODE_PORT)
    env_backend["UNIGURU_ALLOWED_CALLERS"] = "bhiv-assistant,gurukul-platform,internal-testing,uniguru-frontend"
    for key, value in env_overrides.items():
        env_backend[key] = value

    backend_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "uniguru.service.api:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(PYTHON_PORT),
        ],
        cwd=str(ROOT),
        env=env_backend,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    env_node = os.environ.copy()
    env_node["NODE_BACKEND_PORT"] = str(NODE_PORT)
    env_node["UNIGURU_ASK_URL"] = f"{PYTHON_BASE}/ask"
    for key, value in env_overrides.items():
        env_node[key] = value

    node_proc = subprocess.Popen(
        ["node", "src/server.js"],
        cwd=str(ROOT / "node-backend"),
        env=env_node,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    _wait_for_health(f"{PYTHON_BASE}/health")
    _wait_for_health(f"{NODE_BASE}/health")
    return backend_proc, node_proc


def _ask_node(query: str, case_name: str) -> Dict[str, Any]:
    started = time.perf_counter()
    response = requests.post(
        f"{NODE_BASE}/api/v1/chat/query",
        json={
            "query": query,
            "session_id": f"proof-{case_name.lower().replace(' ', '-')}",
            "context": {"caller": "bhiv-assistant", "channel": "demo-safety-proof"},
        },
        timeout=30,
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    payload = response.json()
    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    answer = str(data.get("answer") or "").strip()
    return {
        "case": case_name,
        "query": query,
        "status_code": response.status_code,
        "route": (data.get("routing") or {}).get("route"),
        "decision": data.get("decision"),
        "verification_status": data.get("verification_status"),
        "answer_preview": answer[:220],
        "non_empty_answer": bool(answer),
        "fallback_prefix_present": SAFE_PREFIX in answer,
        "latency_ms": latency_ms,
    }


def _run_queries(cases: List[tuple[str, str]]) -> List[Dict[str, Any]]:
    return [_ask_node(query=q, case_name=name) for name, q in cases]


def _toggle_knowledge_dir(disable: bool) -> None:
    if disable:
        if KNOWLEDGE_BACKUP.exists():
            raise RuntimeError(f"Backup directory already exists: {KNOWLEDGE_BACKUP}")
        if KNOWLEDGE_DIR.exists():
            shutil.move(str(KNOWLEDGE_DIR), str(KNOWLEDGE_BACKUP))
        return
    if KNOWLEDGE_BACKUP.exists():
        if KNOWLEDGE_DIR.exists():
            shutil.rmtree(KNOWLEDGE_DIR)
        shutil.move(str(KNOWLEDGE_BACKUP), str(KNOWLEDGE_DIR))


def _all_non_empty(items: List[Dict[str, Any]]) -> bool:
    return all(item.get("status_code") == 200 and item.get("non_empty_answer") for item in items)


def _any_503(scenarios: List[Dict[str, Any]]) -> bool:
    for scenario in scenarios:
        for result in scenario.get("results", []):
            if int(result.get("status_code") or 0) == 503:
                return True
    return False


def _write_markdown_report(payload: Dict[str, Any]) -> None:
    lines = [
        "# Demo Stability Proof",
        "",
        f"Execution date (UTC): {payload['timestamp_utc']}",
        "",
        "## Summary",
        f"- System stable for demo: `{payload['system_stable_for_demo']}`",
        f"- Any 503 observed: `{payload['any_503_observed']}`",
        f"- All scenarios returned non-empty answers: `{payload['all_scenarios_non_empty_answers']}`",
        "",
        "## Scenarios",
    ]
    for scenario in payload["scenarios"]:
        lines.append("")
        lines.append(f"### {scenario['name']}")
        lines.append(f"- Purpose: {scenario['purpose']}")
        lines.append(f"- Passed: `{scenario['passed']}`")
        for result in scenario["results"]:
            lines.append(
                "- "
                f"{result['case']}: HTTP {result['status_code']}, route `{result['route']}`, "
                f"decision `{result['decision']}`, non-empty answer `{result['non_empty_answer']}`"
            )
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


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    scenarios: List[Dict[str, Any]] = []
    stack: tuple[subprocess.Popen[Any], subprocess.Popen[Any]] | None = None
    knowledge_disabled = False

    try:
        # Scenario 1: Baseline E2E run.
        stack = _start_stack(
            {
                "UNIGURU_API_AUTH_REQUIRED": "false",
                "UNIGURU_LLM_URL": "internal://demo-llm",
            }
        )
        results_1 = _run_queries(
            [
                ("KB Query", "What is a qubit?"),
                ("Religious KB Query", "Who is Mahavira?"),
                ("General LLM Query", "Tell me a short joke."),
                ("Invalid Query", "!!??###"),
                ("System Command Query", "sudo rm -rf /"),
            ]
        )
        scenarios.append(
            {
                "name": "Scenario 1: Baseline End-to-End",
                "purpose": "Prove normal runtime behavior with KB + LLM routing.",
                "results": results_1,
                "passed": _all_non_empty(results_1),
            }
        )
        _stop(stack[1])
        _stop(stack[0])
        stack = None

        # Scenario 2: External LLM endpoint down.
        stack = _start_stack(
            {
                "UNIGURU_API_AUTH_REQUIRED": "false",
                "UNIGURU_LLM_URL": "http://127.0.0.1:65534/unreachable-llm",
            }
        )
        results_2 = _run_queries([("LLM Failure Query", "Explain recursion in simple terms.")])
        scenarios.append(
            {
                "name": "Scenario 2: LLM Endpoint Failure",
                "purpose": "Prove LLM failure still returns safe fallback response.",
                "results": results_2,
                "passed": _all_non_empty(results_2),
            }
        )
        _stop(stack[1])
        _stop(stack[0])
        stack = None

        # Scenario 3: KB unavailable + LLM endpoint down.
        _toggle_knowledge_dir(disable=True)
        knowledge_disabled = True
        stack = _start_stack(
            {
                "UNIGURU_API_AUTH_REQUIRED": "false",
                "UNIGURU_LLM_URL": "http://127.0.0.1:65534/unreachable-llm",
            }
        )
        results_3 = _run_queries(
            [
                ("KB Missing Knowledge Query", "What is a qubit?"),
                ("KB Missing General Query", "What is Python?"),
            ]
        )
        scenarios.append(
            {
                "name": "Scenario 3: KB Failure + LLM Failure",
                "purpose": "Prove demo safety mode under compound failures.",
                "results": results_3,
                "passed": _all_non_empty(results_3),
            }
        )
        _stop(stack[1])
        _stop(stack[0])
        stack = None
        _toggle_knowledge_dir(disable=False)
        knowledge_disabled = False

        # Scenario 4: Auth required but no tokens configured (demo mode fallback).
        stack = _start_stack(
            {
                "UNIGURU_API_AUTH_REQUIRED": "true",
                "UNIGURU_API_TOKEN": "",
                "UNIGURU_API_TOKENS": "",
                "UNIGURU_LLM_URL": "internal://demo-llm",
            }
        )
        health = requests.get(f"{PYTHON_BASE}/health", timeout=10).json()
        results_4 = _run_queries([("Auth Demo Mode Query", "Explain what a function is.")])
        scenarios.append(
            {
                "name": "Scenario 4: Auth Required Without Tokens",
                "purpose": "Prove token OR demo mode behavior.",
                "results": results_4,
                "health_auth_mode": (health.get("auth") or {}).get("mode"),
                "passed": _all_non_empty(results_4)
                and ((health.get("auth") or {}).get("mode") == "demo-no-auth"),
            }
        )

        all_non_empty = all(bool(s.get("passed")) for s in scenarios)
        any_503 = _any_503(scenarios)
        payload = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "system_stable_for_demo": bool(all_non_empty and not any_503),
            "any_503_observed": any_503,
            "all_scenarios_non_empty_answers": all_non_empty,
            "scenarios": scenarios,
        }
        OUTPUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        _write_markdown_report(payload)
        print(str(OUTPUT_JSON))
    finally:
        if stack is not None:
            _stop(stack[1])
            _stop(stack[0])
        if knowledge_disabled:
            _toggle_knowledge_dir(disable=False)


if __name__ == "__main__":
    main()
