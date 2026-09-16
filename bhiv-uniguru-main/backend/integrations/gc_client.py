from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict

logger = logging.getLogger("uniguru.integrations.gc_client")


class GCClient:
    """
    Submits execution payloads to the GC (Governance Constitutional) service for
    authority boundary, hidden-state compliance, and constitutional enforcement validation.
    Env-gated; degrades gracefully when endpoint is not configured.
    """

    def __init__(self) -> None:
        self.enabled = os.getenv("GC_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
        self.base_url = os.getenv("GC_BASE_URL", "").strip().rstrip("/")
        self.token = os.getenv("GC_TOKEN", "").strip()
        self.timeout = float(os.getenv("GC_TIMEOUT_SECONDS", "5.0"))

    def validate_authority(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/gc/validate/authority", payload)

    def validate_hidden_state(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/gc/validate/hidden-state", payload)

    def validate_governance_drift(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/gc/validate/governance-drift", payload)

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
            logger.warning("GC call to %s failed: %s", path, exc)
            return {"live": False, "reason": str(exc), "path": path}

    def is_live(self) -> bool:
        return self.enabled and bool(self.base_url)
