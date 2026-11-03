"""
Immutable Cryptographic Audit Log Emitter
T-GOV-002 — Automated Audit Emitters

Emits append-only, SHA-256 hash-chained audit entries to a JSONL file.
Each entry includes: event, actor, resource, outcome, timestamp, entry_hash,
and prev_hash — forming a tamper-evident chain.

The chain can be verified at any time via ``AuditEmitter.verify_chain()``.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


_GENESIS_HASH = "0" * 64  # sentinel for the first entry


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


class AuditEntry:
    """Immutable audit log entry with cryptographic linkage."""

    __slots__ = (
        "seq",
        "event",
        "actor",
        "resource",
        "outcome",
        "metadata",
        "timestamp",
        "prev_hash",
        "entry_hash",
    )

    def __init__(
        self,
        seq: int,
        event: str,
        actor: str,
        resource: str,
        outcome: str,
        metadata: Dict[str, Any],
        timestamp: str,
        prev_hash: str,
    ) -> None:
        self.seq = seq
        self.event = event
        self.actor = actor
        self.resource = resource
        self.outcome = outcome
        self.metadata = metadata
        self.timestamp = timestamp
        self.prev_hash = prev_hash
        # Hash is computed over all fields except entry_hash itself
        self.entry_hash = _sha256(
            json.dumps(
                {
                    "seq": seq,
                    "event": event,
                    "actor": actor,
                    "resource": resource,
                    "outcome": outcome,
                    "metadata": metadata,
                    "timestamp": timestamp,
                    "prev_hash": prev_hash,
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seq": self.seq,
            "event": self.event,
            "actor": self.actor,
            "resource": self.resource,
            "outcome": self.outcome,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "prev_hash": self.prev_hash,
            "entry_hash": self.entry_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEntry":
        entry = cls(
            seq=int(data["seq"]),
            event=str(data["event"]),
            actor=str(data["actor"]),
            resource=str(data["resource"]),
            outcome=str(data["outcome"]),
            metadata=dict(data.get("metadata") or {}),
            timestamp=str(data["timestamp"]),
            prev_hash=str(data["prev_hash"]),
        )
        if data.get("entry_hash") != entry.entry_hash:
            raise ValueError(f"Audit entry hash mismatch at sequence {entry.seq}.")
        return entry


class AuditEmitter:
    """Thread-safe, append-only, hash-chained audit log.

    Parameters
    ----------
    log_path:
        Path to the JSONL audit log file. Created on first emit.
    """

    def __init__(self, log_path: str | Path) -> None:
        self._path = Path(log_path)
        self._lock = threading.Lock()
        self._seq, self._last_hash = self._bootstrap()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def emit(
        self,
        event: str,
        actor: str,
        resource: str,
        outcome: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """Append an immutable audit entry and return it."""
        with self._lock:
            if self._path.exists() and not self.verify_chain()["valid"]:
                raise ValueError("Cannot append to an invalid audit chain.")
            entry = AuditEntry(
                seq=self._seq,
                event=event,
                actor=actor,
                resource=resource,
                outcome=outcome,
                metadata=metadata or {},
                timestamp=_utc_now_iso(),
                prev_hash=self._last_hash,
            )
            self._append(entry)
            self._seq += 1
            self._last_hash = entry.entry_hash
        return entry

    def verify_chain(self) -> Dict[str, Any]:
        """Read the log file and verify the full hash chain.

        Returns a dict with ``valid`` (bool), ``entry_count``, and
        ``broken_at_seq`` (None if chain is intact).
        """
        try:
            entries = self._read_all()
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return {"valid": False, "entry_count": 0, "broken_at_seq": None, "reason": "malformed_entry"}
        if not entries:
            return {"valid": True, "entry_count": 0, "broken_at_seq": None}
        result = self._verify_entries(entries)
        result["entry_count"] = len(entries)
        return result

    def tail(self, n: int = 10) -> List[Dict[str, Any]]:
        """Return the last n audit entries as dicts."""
        entries = self._read_all()
        return [e.to_dict() for e in entries[-n:]]

    @property
    def last_hash(self) -> str:
        with self._lock:
            return self._last_hash

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _bootstrap(self) -> tuple[int, str]:
        """Load existing log to determine current seq and last_hash."""
        if not self._path.exists():
            return 0, _GENESIS_HASH
        entries = self._read_all()
        if not entries:
            return 0, _GENESIS_HASH
        last = entries[-1]
        return last.seq + 1, last.entry_hash

    def _append(self, entry: AuditEntry) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.to_dict(), ensure_ascii=True, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def _read_all(self) -> List[AuditEntry]:
        if not self._path.exists():
            return []
        entries: List[AuditEntry] = []
        with self._path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                entries.append(AuditEntry.from_dict(json.loads(line)))
        return entries

    @staticmethod
    def _verify_entries(entries: List[AuditEntry]) -> Dict[str, Any]:
        prev = _GENESIS_HASH
        for expected_seq, entry in enumerate(entries):
            if entry.seq != expected_seq or entry.prev_hash != prev:
                return {"valid": False, "broken_at_seq": entry.seq}
            recomputed = _sha256(json.dumps({
                "seq": entry.seq,
                "event": entry.event,
                "actor": entry.actor,
                "resource": entry.resource,
                "outcome": entry.outcome,
                "metadata": entry.metadata,
                "timestamp": entry.timestamp,
                "prev_hash": entry.prev_hash,
            }, ensure_ascii=True, sort_keys=True))
            if recomputed != entry.entry_hash:
                return {"valid": False, "broken_at_seq": entry.seq}
            prev = entry.entry_hash
        return {"valid": True, "broken_at_seq": None}
