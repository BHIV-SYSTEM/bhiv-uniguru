from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict

logger = logging.getLogger("uniguru.integrations.insightflow_client")

# Vijay's canonical InsightFlow ingest path (from sovereign stack config)
_INGEST_PATH = "/telemetry/ingest"


class InsightFlowClient:
    """
    Emits runtime telemetry to InsightFlow via the canonical /telemetry/ingest endpoint.
    Auth: Bearer token from INSIGHTFLOW_TOKEN (flow_secret_789 per Vijay's sovereign config).
    Env-gated; degrades gracefully when base URL is not configured.

    Set INSIGHTFLOW_BASE_URL to Vijay's deployed Flow service URL to activate.
    Local dev only: http://127.0.0.1:8002 (not reachable from Render deployment).
    """

    def __init__(self) -> None:
        self.enabled = os.getenv("INSIGHTFLOW_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
        self.base_url = (
            os.getenv("INSIGHTFLOW_BASE_URL") or os.getenv("INSIGHTFLOW_ENDPOINT", "")
        ).strip().rstrip("/")
        self.token = os.getenv("INSIGHTFLOW_TOKEN", "").strip()
        self.timeout = float(os.getenv("INSIGHTFLOW_TIMEOUT_SECONDS", "3.0"))

    def emit_trace(self, trace_payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._ingest({"type": "trace", **trace_payload})

    def emit_decision(self, decision_payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._ingest({"type": "decision", **decision_payload})

    def emit_metric(self, metric_payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._ingest({"type": "metric", **metric_payload})

    def emit_failure(self, failure_payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._ingest({"type": "failure", **failure_payload})

    def _ingest(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled or not self.base_url:
            return {"live": False, "reason": "not_configured", "path": _INGEST_PATH}
        url = f"{self.base_url}{_INGEST_PATH}"
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        headers: Dict[str, str] = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(url=url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                response_body = resp.read().decode("utf-8")
                data = json.loads(response_body) if response_body.strip() else {}
                return {"live": True, "status": resp.status, "data": data}
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("InsightFlow ingest failed: %s", exc)
            return {"live": False, "reason": str(exc), "path": _INGEST_PATH}

    def is_live(self) -> bool:
        return self.enabled and bool(self.base_url)
