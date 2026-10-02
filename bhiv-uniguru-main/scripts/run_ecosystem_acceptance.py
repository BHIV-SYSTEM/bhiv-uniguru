from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
REVIEW = ROOT / "review_packets"
INTEGRATION_PROOF = REVIEW / "integration_proof"
VALIDATION_REPORTS = REVIEW / "validation_reports"
DEPLOYMENT_PROOF = REVIEW / "deployment_proof"
LOGS = REVIEW / "logs"
SCREENSHOTS = REVIEW / "screenshots"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("UNIGURU_API_AUTH_REQUIRED", "false")

from memory.constitutional_semantic_memory import stable_hash
from service.uniguru_runtime_api import app


QUERY = "What is the Bhagavad Gita?"
TRACE_ID = "ecosystem_acceptance_live"
SCREENSHOT_BUCKETS = [
    "Runtime execution",
    "TANTRA integration",
    "Bucket telemetry",
    "InsightFlow",
    "API responses",
    "Test execution",
    "Benchmarks",
    "Dashboards",
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _capture_response(client: TestClient, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
    started = time.perf_counter()
    response = getattr(client, method.lower())(path, **kwargs)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    try:
        body: Any = response.json()
    except ValueError:
        body = response.text
    return {
        "method": method.upper(),
        "path": path,
        "status_code": response.status_code,
        "elapsed_ms": elapsed_ms,
        "body": body,
    }


def _assert_ok(capture: Dict[str, Any]) -> None:
    if int(capture["status_code"]) >= 400:
        raise RuntimeError(f"{capture['method']} {capture['path']} failed: {capture['status_code']}")


def _write_packet_docs(summary: Dict[str, Any]) -> None:
    trace_id = summary["trace_id"]
    verdict = summary["verdict"]
    replay_verified = summary["replay"]["body"]["replay_verified"]
    execution = summary["execution"]["body"]
    mitra = summary["mitra"]["body"]

    _write_text(
        REVIEW / "execution_summary.md",
        "\n".join(
            [
                "# Execution Summary",
                "",
                "## Live ecosystem execution",
                f"- Generated at: `{summary['generated_at']}`",
                f"- Verdict: `{verdict}`",
                f"- Trace id: `{trace_id}`",
                "- Runtime endpoint: `POST /runtime/ecosystem/execute`",
                "- Replay endpoint: `POST /runtime/ecosystem/replay`",
                "- Mitra endpoint: `POST /mitra/ecosystem/ask`",
                "",
                "## Acceptance evidence",
                f"- Vijay replay safe: `{execution['vijay_validation']['replay_safe']}`",
                f"- TANTRA contract bound: `{execution['tantra_contract']['contract_bound']}`",
                f"- Bucket telemetry emitted: `{execution['bucket_telemetry']['emitted']}`",
                f"- InsightFlow trace complete: `{execution['insightflow_observability']['trace_complete']}`",
                f"- GC authority enforced: `{execution['gc_validation']['authority_enforced']}`",
                f"- MDU schema compatible: `{execution['mdu_validation']['schema_compatible']}`",
                f"- Cross-service replay verified: `{replay_verified}`",
                f"- Mitra downstream consumable: `{mitra['downstream_consumable']}`",
                "",
                "## Proof locations",
                "- `review_packets/integration_proof/ecosystem_execution_latest.json`",
                "- `review_packets/integration_proof/replay_verification_latest.json`",
                "- `review_packets/validation_reports/ecosystem_acceptance_report.json`",
                "- `review_packets/logs/ecosystem_acceptance_api_responses.json`",
            ]
        )
        + "\n",
    )

    _write_text(
        REVIEW / "REVIEW_PACKET.md",
        "\n".join(
            [
                "# REVIEW_PACKET.md - UniGuru BHIV Ecosystem Integration",
                "",
                f"Generated at: `{summary['generated_at']}`",
                f"Status: `{verdict}`",
                "",
                "## Scope",
                "UniGuru participates in the BHIV execution chain as an internal intelligence capability while exposing only governed, redacted capability output to Mitra.",
                "",
                "## Live Evidence",
                "- Vijay integration proof: `review_packets/integration_proof/ecosystem_execution_latest.json` -> `vijay_validation`",
                "- TANTRA integration proof: `review_packets/integration_proof/ecosystem_execution_latest.json` -> `tantra_contract`",
                "- Bucket telemetry evidence: `review_packets/integration_proof/bucket_ecosystem_acceptance_live.json`",
                "- InsightFlow evidence: `review_packets/integration_proof/ecosystem_execution_latest.json` -> `insightflow_observability`",
                "- GC validation evidence: `review_packets/integration_proof/ecosystem_execution_latest.json` -> `gc_validation`",
                "- MDU validation evidence: `review_packets/integration_proof/ecosystem_execution_latest.json` -> `mdu_validation`",
                "- Cross-service replay logs: `review_packets/integration_proof/replay_verification_latest.json`",
                "- API response logs: `review_packets/logs/ecosystem_acceptance_api_responses.json`",
                "- Deployment validation: `review_packets/deployment_proof/ecosystem_deployment_validation.json`",
                "",
                "## Runtime Flow",
                "`Mitra/BHIV request -> /runtime/ecosystem/execute -> deterministic Kosha pipeline -> Vijay replay validation -> TANTRA contract -> Bucket telemetry -> InsightFlow observability -> GC authority validation -> MDU schema/provenance validation -> governed response`",
                "",
                "## Integration Points",
                "- Internal BHIV: `POST /runtime/ecosystem/execute` returns full integration evidence.",
                "- Replay validation: `POST /runtime/ecosystem/replay` verifies stable runtime, contract, authority and lineage fields.",
                "- Mitra-facing: `POST /mitra/ecosystem/ask` returns answer, verification state, replay status, contract schema and evidence pointers without internal governance payloads.",
                "- Health: `GET /health`, readiness: `GET /ready`, metrics: `GET /metrics`.",
                "",
                "## Known Limits",
                "- This workspace run validates local production parity through FastAPI request handling; external BHIV service deployment still needs environment-specific endpoint URLs and credentials.",
                "- Bucket evidence is file-backed unless `UNIGURU_BUCKET_TELEMETRY_ENDPOINT` is configured in deployment.",
                "- Screenshot folders contain evidence notes for API/runtime artifacts; no UI dashboard capture was required for this backend-only convergence run.",
            ]
        )
        + "\n",
    )


def _write_screenshot_notes(summary: Dict[str, Any]) -> None:
    for bucket in SCREENSHOT_BUCKETS:
        _write_text(
            SCREENSHOTS / bucket / "evidence_note.md",
            "\n".join(
                [
                    f"# {bucket}",
                    "",
                    "Backend integration evidence for this bucket is captured in:",
                    "- `review_packets/validation_reports/ecosystem_acceptance_report.json`",
                    "- `review_packets/logs/ecosystem_acceptance_api_responses.json`",
                    "- `review_packets/integration_proof/ecosystem_execution_latest.json`",
                    "",
                    f"Trace id: `{summary['trace_id']}`",
                ]
            )
            + "\n",
        )


def main() -> None:
    client = TestClient(app)
    request_body = {"query": QUERY, "trace_id": TRACE_ID, "emit_proof": True}
    health = _capture_response(client, "GET", "/health")
    ready = _capture_response(client, "GET", "/ready")
    metrics = _capture_response(client, "GET", "/metrics")
    execution = _capture_response(client, "POST", "/runtime/ecosystem/execute", json=request_body)
    replay = _capture_response(client, "POST", "/runtime/ecosystem/replay", json=request_body)
    mitra = _capture_response(client, "POST", "/mitra/ecosystem/ask", json=request_body)

    for capture in [health, ready, metrics, execution, replay, mitra]:
        _assert_ok(capture)

    execution_body = execution["body"]
    replay_body = replay["body"]
    checks = {
        "health_ok": health["body"]["status"] == "ok",
        "ready_ok": ready["body"]["status"] == "ready",
        "metrics_exposed": "uniguru_ecosystem_runtime_ready" in str(metrics["body"]),
        "vijay_replay_safe": execution_body["vijay_validation"]["replay_safe"] is True,
        "tantra_contract_bound": execution_body["tantra_contract"]["contract_bound"] is True,
        "bucket_emitted": execution_body["bucket_telemetry"]["emitted"] is True,
        "insightflow_trace_complete": execution_body["insightflow_observability"]["trace_complete"] is True,
        "gc_authority_enforced": execution_body["gc_validation"]["authority_enforced"] is True,
        "mdu_schema_compatible": execution_body["mdu_validation"]["schema_compatible"] is True,
        "cross_service_replay_verified": replay_body["replay_verified"] is True,
        "mitra_payload_redacted": all(key not in mitra["body"] for key in ["vijay_validation", "gc_validation", "mdu_validation"]),
    }
    summary = {
        "schema": "UNIGURU_ECOSYSTEM_ACCEPTANCE_REPORT_V1",
        "generated_at": _utc_now_iso(),
        "trace_id": TRACE_ID,
        "query_hash": stable_hash({"query": QUERY})[:16],
        "verdict": "ACCEPTED" if all(checks.values()) else "REJECTED",
        "checks": checks,
        "health": health,
        "ready": ready,
        "metrics": metrics,
        "execution": execution,
        "replay": replay,
        "mitra": mitra,
    }
    summary["acceptance_hash"] = stable_hash(summary)

    _write_json(VALIDATION_REPORTS / "ecosystem_acceptance_report.json", summary)
    _write_json(LOGS / "ecosystem_acceptance_api_responses.json", summary)
    _write_json(
        DEPLOYMENT_PROOF / "ecosystem_deployment_validation.json",
        {
            "schema": "UNIGURU_ECOSYSTEM_DEPLOYMENT_VALIDATION_V1",
            "generated_at": summary["generated_at"],
            "health_status": health["body"],
            "ready_status": ready["body"],
            "metrics_contains_runtime_ready": checks["metrics_exposed"],
            "accepted": summary["verdict"] == "ACCEPTED",
            "trace_id": TRACE_ID,
        },
    )
    _write_screenshot_notes(summary)
    _write_packet_docs(summary)
    print(json.dumps({"verdict": summary["verdict"], "trace_id": TRACE_ID, "checks": checks}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
