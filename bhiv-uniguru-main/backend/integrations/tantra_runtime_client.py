from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("uniguru.integrations.tantra_runtime_client")


class TantraRuntimeClient:
    """
    Live HTTP client for the Vijay TANTRA SDK runtime.
    All calls are env-gated; if the endpoint is not configured the caller
    receives a structured 'not_configured' response so the pipeline can
    continue without crashing.
    """

    def __init__(self) -> None:
        self.enabled = os.getenv("TANTRA_SDK_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
        self.base_url = os.getenv("TANTRA_SDK_BASE_URL", "").strip().rstrip("/")
        self.token = os.getenv("TANTRA_SDK_TOKEN", "").strip()
        self.timeout = float(os.getenv("TANTRA_SDK_TIMEOUT_SECONDS", "5.0"))

    # ------------------------------------------------------------------
    # Runtime Contract
    # ------------------------------------------------------------------
    def submit_execution_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/runtime/execution-event", payload)

    # ------------------------------------------------------------------
    # Replay Contract
    # ------------------------------------------------------------------
    def submit_replay_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/runtime/replay-event", payload)

    # ------------------------------------------------------------------
    # Trace Contract
    # ------------------------------------------------------------------
    def submit_trace(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/runtime/trace", payload)

    # ------------------------------------------------------------------
    # Authority Contract
    # ------------------------------------------------------------------
    def validate_authority(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/runtime/authority/validate", payload)

    # ------------------------------------------------------------------
    # Capability Contract
    # ------------------------------------------------------------------
    def register_capability(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/runtime/capability/register", payload)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled or not self.base_url:
            return {"live": False, "reason": "not_configured", "path": path}
        url = f"{self.base_url}{path}"
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
            logger.warning("TANTRA SDK call to %s failed: %s", path, exc)
            return {"live": False, "reason": str(exc), "path": path}

    def is_live(self) -> bool:
        return self.enabled and bool(self.base_url)
