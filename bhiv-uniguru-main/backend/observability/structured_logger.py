"""
Structured Logger — Production Observability
=============================================
Emits machine-readable JSON lines for every request.
Each log line contains: timestamp, request_id, route, latency_ms,
verification_status, confidence, domain, signal_count, error_class.

Compatible with: stdout log aggregators (Loki, CloudWatch, Datadog, etc.)
Output file: logs/uniguru_structured.jsonl (relative to repo root)

Usage — in FastAPI middleware:
    from observability.structured_logger import StructuredLogger
    logger = StructuredLogger()
    logger.log_request(...)
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

_PYTHON_LOG = logging.getLogger("uniguru.observability.structured_logger")

# Determine log output path relative to repo root
_REPO_ROOT = Path(__file__).parent.parent.parent
_LOG_DIR = _REPO_ROOT / "logs"
_LOG_FILE = _LOG_DIR / "uniguru_structured.jsonl"


class StructuredLogger:
    """
    Thread-safe JSON structured logger.
    Writes one JSON object per line to file AND stdout.
    """

    _instance: Optional["StructuredLogger"] = None
    _lock = threading.Lock()

    def __init__(self, log_path: Optional[Path] = None, write_stdout: bool = True) -> None:
        self._log_path = log_path or _LOG_FILE
        self._write_stdout = write_stdout
        self._file_lock = threading.Lock()
        # Ensure log directory exists
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # pragma: no cover
            _PYTHON_LOG.warning("Could not create log directory: %s", exc)

    @classmethod
    def get_instance(cls) -> "StructuredLogger":
        """Return singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def log_request(
        self,
        *,
        request_id: str,
        route: str,
        method: str = "POST",
        latency_ms: float,
        status_code: int = 200,
        verification_status: Optional[str] = None,
        confidence: Optional[float] = None,
        domain: Optional[str] = None,
        signal_count: Optional[int] = None,
        error_class: Optional[str] = None,
        session_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Emit a structured log entry. Returns the dict that was written.
        """
        entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "service": "uniguru-live-reasoning",
            "level": "ERROR" if status_code >= 500 else "WARN" if status_code >= 400 else "INFO",
            "request_id": request_id,
            "method": method,
            "route": route,
            "status_code": status_code,
            "latency_ms": round(latency_ms, 3),
        }
        if verification_status is not None:
            entry["verification_status"] = verification_status
        if confidence is not None:
            entry["confidence"] = round(float(confidence), 4)
        if domain is not None:
            entry["domain"] = domain
        if signal_count is not None:
            entry["signal_count"] = signal_count
        if error_class is not None:
            entry["error_class"] = error_class
        if session_id is not None:
            entry["session_id"] = session_id
        if extra:
            entry["extra"] = extra

        self._write(entry)
        return entry

    def log_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Emit a non-request structured log event (e.g., startup, shutdown, metric flush)."""
        entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "service": "uniguru-live-reasoning",
            "level": "INFO",
            "event_type": event_type,
            **payload,
        }
        self._write(entry)
        return entry

    def get_recent_entries(self, n: int = 10) -> list:
        """Read the last N entries from the log file."""
        try:
            if not self._log_path.exists():
                return []
            lines = self._log_path.read_text(encoding="utf-8").splitlines()
            recent = lines[-n:]
            result = []
            for line in recent:
                line = line.strip()
                if line:
                    try:
                        result.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            return result
        except Exception as exc:
            _PYTHON_LOG.warning("Could not read log file: %s", exc)
            return []

    def _write(self, entry: Dict[str, Any]) -> None:
        line = json.dumps(entry, ensure_ascii=True, separators=(",", ":")) + "\n"
        if self._write_stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
        try:
            with self._file_lock:
                with open(self._log_path, "a", encoding="utf-8") as fh:
                    fh.write(line)
        except Exception as exc:  # pragma: no cover
            _PYTHON_LOG.warning("Structured log write failed: %s", exc)


# Module-level convenience singleton
_default_logger = StructuredLogger.get_instance()


def log_request(**kwargs: Any) -> Dict[str, Any]:
    """Module-level shortcut to the singleton logger."""
    return _default_logger.log_request(**kwargs)


def log_event(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level shortcut to the singleton logger."""
    return _default_logger.log_event(event_type, payload)


def get_recent_entries(n: int = 10) -> list:
    """Module-level shortcut to the singleton logger."""
    return _default_logger.get_recent_entries(n)
