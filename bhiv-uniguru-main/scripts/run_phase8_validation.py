from __future__ import annotations

import json
import os
import signal
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
OUTPUT_PATH = ROOT / "demo_logs" / "phase8_test_outputs.json"


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


def _terminate(proc: subprocess.Popen[Any]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def _post_node_query(query: str, case_name: str) -> Dict[str, Any]:
    started = time.perf_counter()
    response = requests.post(
        f"{NODE_BASE}/api/v1/chat/query",
        json={
            "query": query,
            "session_id": f"phase8-{case_name.lower().replace(' ', '-')}",
            "context": {"caller": "bhiv-assistant", "channel": "phase8-validation"},
        },
        timeout=25,
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    payload = response.json()
    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    answer = str(data.get("answer") or "").strip()
    return {
        "name": case_name,
        "query": query,
        "status_code": response.status_code,
        "latency_ms": latency_ms,
        "success": bool(payload.get("success")) if isinstance(payload, dict) else False,
        "degraded": bool(payload.get("degraded")) if isinstance(payload, dict) else False,
        "decision": data.get("decision"),
        "verification_status": data.get("verification_status"),
        "route": (data.get("routing") or {}).get("route"),
        "answer_preview": answer[:200],
        "has_answer": bool(answer),
        "reason": data.get("reason"),
    }


def _start_backend() -> subprocess.Popen[Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "backend")
    env["UNIGURU_HOST"] = "127.0.0.1"
    env["UNIGURU_PORT"] = str(PYTHON_PORT)
    env["UNIGURU_API_AUTH_REQUIRED"] = "false"
    env["UNIGURU_LLM_URL"] = env.get("UNIGURU_LLM_URL", "internal://demo-llm")
    env["UNIGURU_ALLOWED_CALLERS"] = (
        "bhiv-assistant,gurukul-platform,internal-testing,uniguru-frontend"
    )
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "uniguru.service.api:app", "--host", "127.0.0.1", "--port", str(PYTHON_PORT)],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _start_node() -> subprocess.Popen[Any]:
    env = os.environ.copy()
    env["NODE_BACKEND_PORT"] = str(NODE_PORT)
    env["UNIGURU_ASK_URL"] = f"{PYTHON_BASE}/ask"
    return subprocess.Popen(
        ["node", "src/server.js"],
        cwd=str(ROOT / "node-backend"),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    backend_proc = _start_backend()
    node_proc = _start_node()

    try:
        _wait_for_health(f"{PYTHON_BASE}/health")
        _wait_for_health(f"{NODE_BASE}/health")

        test_cases = [
            ("KB Query", "What is a qubit?"),
            ("Religious KB Query", "Who is Mahavira?"),
            ("General Query", "Explain Python lists in simple terms."),
            ("Invalid Query", "!!??###"),
            ("System Command Query", "sudo rm -rf /"),
        ]
        results = [_post_node_query(query=q, case_name=name) for name, q in test_cases]
        all_ok = all(item["status_code"] == 200 and item["has_answer"] for item in results)

        output = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "python_health": requests.get(f"{PYTHON_BASE}/health", timeout=10).json(),
            "python_ready": requests.get(f"{PYTHON_BASE}/ready", timeout=10).json(),
            "node_health": requests.get(f"{NODE_BASE}/health", timeout=10).json(),
            "results": results,
            "all_ok": all_ok,
        }
        OUTPUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(str(OUTPUT_PATH))
    finally:
        _terminate(node_proc)
        _terminate(backend_proc)


if __name__ == "__main__":
    main()
