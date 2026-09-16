from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict


logger = logging.getLogger("uniguru.integrations.core_reader")


class CoreReaderClient:
    """
    Read-only Core knowledge integration for reference/domain alignment.
    """

    def __init__(self) -> None:
        self.enabled = os.getenv("UNIGURU_CORE_READER_ENABLED", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.base_url = os.getenv("UNIGURU_CORE_BASE_URL", "").strip().rstrip("/")
        self.token = os.getenv("UNIGURU_CORE_TOKEN", "").strip()
        self.timeout_seconds = float(os.getenv("UNIGURU_CORE_TIMEOUT_SECONDS", "2.0"))

    def align_reference(self, reference: Dict[str, Any]) -> Dict[str, Any]:
        concept_id = str(reference.get("concept_id") or "").strip()
        domain = str(reference.get("domain") or "").strip()
        result: Dict[str, Any] = {
            "enabled": self.enabled,
            "read_only": True,
            "concept_id": concept_id,
            "domain": domain,
            "registry_aligned": False,
        }
        if not self.enabled or not self.base_url or not concept_id:
            return result

        endpoint = f"{self.base_url}/knowledge/reference/{urllib.parse.quote(concept_id)}"
        request = urllib.request.Request(endpoint, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Core read failed for concept %s: %s", concept_id, exc)
            return result

        core_domain = str(payload.get("domain") or "").strip()
        result["registry_aligned"] = bool(core_domain and core_domain == domain)
        result["core_reference_version"] = payload.get("version")
        result["domain_valid"] = result["registry_aligned"]
        return result

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
