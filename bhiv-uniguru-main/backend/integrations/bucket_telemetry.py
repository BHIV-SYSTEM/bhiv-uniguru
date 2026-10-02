from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional


logger = logging.getLogger("uniguru.integrations.bucket_telemetry")


@dataclass(frozen=True)
class TelemetryEvent:
    event: str
    query_hash: str
    route: str
    verification_status: str
    latency: float
    caller: Optional[str]
    session_id: Optional[str]
    ontology_reference: Optional[Dict[str, Any]] = None
    routing: Optional[Dict[str, Any]] = None
    decision: Optional[str] = None


class BucketTelemetryClient:
    """
    Emits metadata-only telemetry events to Bucket.
    Never sends raw query text.
    """

    def __init__(self) -> None:
        self.enabled = os.getenv("UNIGURU_BUCKET_TELEMETRY_ENABLED", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.endpoint = os.getenv("UNIGURU_BUCKET_TELEMETRY_ENDPOINT", "").strip()
        self.token = os.getenv("UNIGURU_BUCKET_TELEMETRY_TOKEN", "").strip()
        self.timeout_seconds = float(os.getenv("UNIGURU_BUCKET_TELEMETRY_TIMEOUT_SECONDS", "2.0"))

    def emit(self, event: TelemetryEvent) -> bool:
        if not self.enabled or not self.endpoint:
            return False

        payload = {
            "event": event.event,
            "query_hash": event.query_hash,
            "route": event.route,
            "verification_status": event.verification_status,
            "latency": round(float(event.latency), 3),
            "caller": event.caller,
            "session_id": event.session_id,
            "ontology_reference": event.ontology_reference,
            "routing": event.routing or {"route": event.route},
            "decision": event.decision,
            "timestamp_ms": int(time.time() * 1000),
        }
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(
            url=self.endpoint,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds):
                return True
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            logger.warning("Bucket telemetry emit failed: %s", exc)
            return False
