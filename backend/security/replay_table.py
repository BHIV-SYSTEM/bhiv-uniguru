"""
Replay Mitigation Table
T-GOV-002 — Replay-Proof Verification

Tracks consumed JWT IDs (jti) and arbitrary nonces to prevent replay attacks.
Entries expire automatically after the token's exp timestamp (+ leeway).
Optionally persists the seen-set to a file for cross-process durability.
"""
from __future__ import annotations

import json
import os
import threading
import time
import tempfile
from pathlib import Path
from typing import Dict, Optional


class ReplayMitigationTable:
    """Thread-safe store of consumed jti / nonce values.

    Parameters
    ----------
    persist_path:
        Optional file path for durable persistence. If set, the table is
        loaded on construction and flushed on every write.
    default_ttl_seconds:
        TTL used when no explicit expiry is provided (default 3600 s).
    leeway_seconds:
        Extra seconds added to token exp before eviction (default 30 s).
    """

    def __init__(
        self,
        persist_path: Optional[str] = None,
        default_ttl_seconds: int = 3600,
        leeway_seconds: int = 30,
    ) -> None:
        self._lock = threading.Lock()
        # {jti: expiry_unix_timestamp}
        self._seen: Dict[str, float] = {}
        self._default_ttl = default_ttl_seconds
        self._leeway = leeway_seconds
        self._persist_path = Path(persist_path) if persist_path else None
        if self._persist_path and self._persist_path.exists():
            self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_replayed(self, jti: str) -> bool:
        """Return True if this jti has already been consumed and not yet expired."""
        self._evict_expired()
        with self._lock:
            return jti in self._seen

    def consume(self, jti: str, exp: Optional[int] = None) -> None:
        """Mark a jti as consumed.

        Raises ``ValueError`` if the jti was already consumed (replay detected).
        """
        with self._lock:
            now = time.time()
            self._evict_expired_locked(now)
            if jti in self._seen:
                raise ValueError(f"Replay detected: jti '{jti}' has already been used.")
            expiry = float(exp + self._leeway) if exp else now + self._default_ttl
            self._seen[jti] = expiry
            self._flush_locked()

    def try_consume(self, jti: str, exp: Optional[int] = None) -> bool:
        """Consume jti if not replayed. Returns False (without raising) on replay."""
        try:
            self.consume(jti, exp)
            return True
        except ValueError:
            return False

    def size(self) -> int:
        """Return the number of active (non-expired) entries."""
        self._evict_expired()
        with self._lock:
            return len(self._seen)

    def clear(self) -> None:
        """Remove all entries (test/admin use only)."""
        with self._lock:
            self._seen.clear()
            self._flush_locked()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evict_expired(self) -> None:
        now = time.time()
        with self._lock:
            self._evict_expired_locked(now)

    def _evict_expired_locked(self, now: float) -> None:
        expired = [jti for jti, exp in self._seen.items() if exp <= now]
        for jti in expired:
            del self._seen[jti]

    def _flush(self) -> None:
        if not self._persist_path:
            return
        with self._lock:
            self._flush_locked()

    def _flush_locked(self) -> None:
        if not self._persist_path:
            return
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot = dict(self._seen)
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{self._persist_path.name}.",
            suffix=".tmp",
            dir=str(self._persist_path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(snapshot, ensure_ascii=True, sort_keys=True))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self._persist_path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def _load(self) -> None:
        try:
            raw = json.loads(self._persist_path.read_text(encoding="utf-8"))  # type: ignore[union-attr]
            if not isinstance(raw, dict):
                raise ValueError("replay store must contain a JSON object")
            now = time.time()
            with self._lock:
                self._seen = {k: float(v) for k, v in raw.items() if float(v) > now}
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise RuntimeError("Replay store could not be loaded; refusing requests until repaired.") from exc
