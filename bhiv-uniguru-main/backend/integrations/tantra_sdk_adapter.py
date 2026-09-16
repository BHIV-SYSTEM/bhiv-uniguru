from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class TantraSdkAdapter:
    """Adapts UniGuru runtime execution into TANTRA execution-event payloads."""

    def __init__(self, schema_path: Optional[Path | str] = None) -> None:
        self.schema_path = self._resolve_schema_path(schema_path)
        self.schema = self._load_schema(self.schema_path)

    def _resolve_schema_path(self, schema_path: Optional[Path | str]) -> Optional[Path]:
        if schema_path:
            return Path(schema_path)

        candidates = [
            Path(os.getenv("TANTARA_ECOSYSTEM_PATH", "")) / "execution_sdk" / "v1" / "schemas" / "execution_event.v1.0.0.json",
            Path(__file__).resolve().parents[1] / "contracts" / "tantra_execution_event_schema.json",
        ]
        for candidate in candidates:
            if candidate and candidate.exists():
                return candidate
        return None

    def _load_schema(self, schema_path: Optional[Path]) -> Optional[Dict[str, Any]]:
        if schema_path and schema_path.exists():
            try:
                return json.loads(schema_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None
        return self._default_schema()

    def _default_schema(self) -> Dict[str, Any]:
        return {
            "title": "Execution Event",
            "required": [
                "schema_version",
                "trace_id",
                "timestamp",
                "ownership",
                "provenance",
                "compatibility",
                "validation_status",
                "execution_id",
                "command",
                "status",
                "subject_id",
                "outcome",
                "duration_ms",
                "related_trace_ids",
            ],
        }

    def build_execution_event(
        self,
        *,
        trace_id: str,
        query: str,
        verification_status: str,
        answer: Optional[str] = None,
        domain: Optional[str] = None,
        duration_ms: int = 0,
        subject_id: str = "uniguru_runtime",
    ) -> Dict[str, Any]:
        payload = {
            "schema_version": "execution_event.v1.0.0",
            "trace_id": trace_id,
            "timestamp": self._utc_now_iso(),
            "ownership": "uniguru",
            "provenance": {
                "source_system": "uniguru_backend",
                "environment": os.getenv("UNIGURU_ENV", "local"),
                "version": "1.0.0",
                "schema_source": str(self.schema_path) if self.schema_path else "embedded_fallback",
            },
            "compatibility": {
                "supported_schema": "execution_event.v1.0.0",
                "adapter": "TantraSdkAdapter",
            },
            "validation_status": "valid",
            "execution_id": f"exec_{trace_id}",
            "command": query,
            "status": "completed",
            "subject_id": subject_id,
            "outcome": {
                "verification_status": str(verification_status or "UNVERIFIED").upper(),
                "answer": answer,
                "domain": domain or "ecosystem",
            },
            "duration_ms": int(max(0, duration_ms)),
            "related_trace_ids": [trace_id],
        }
        return payload

    def validate_payload(self, payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
        required_fields = (self.schema or {}).get("required", [])
        missing = [field for field in required_fields if field not in payload]
        if missing:
            return False, missing
        return True, []

    def emit_execution_event(self, **kwargs: Any) -> Dict[str, Any]:
        payload = self.build_execution_event(**kwargs)
        is_valid, missing = self.validate_payload(payload)
        if not is_valid:
            payload["validation_status"] = "invalid"
            payload.setdefault("validation_errors", missing)
        return payload

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
