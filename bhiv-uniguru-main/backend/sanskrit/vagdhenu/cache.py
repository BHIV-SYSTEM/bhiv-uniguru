"""Deterministic audio caching for Vāgdhenu Sanskrit Chants."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional


def compute_cache_key(
    text: str,
    meter: Optional[str] = None,
    settings: Optional[Any] = None,
    *args: Any,
) -> str:
    """Creates a deterministic SHA-256 cache key from normalized Sanskrit text and generation parameters."""
    norm_text = " ".join(str(text or "").split()).strip()
    norm_meter = str(meter or "auto").strip().lower()
    if isinstance(settings, dict):
        extra = json.dumps(settings, sort_keys=True)
    elif settings is not None:
        extra = f"{settings}:" + ":".join(str(a) for a in args)
    else:
        extra = ""
    payload = f"{norm_text}|{norm_meter}|{extra}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


compute_audio_cache_key = compute_cache_key



class VagdhenuAudioCache:
    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.cache_dir / "cache_index.json"
        self._index: Dict[str, Dict[str, Any]] = {}
        self._load_index()

    def _load_index(self) -> None:
        if self.index_file.exists():
            try:
                self._index = json.loads(self.index_file.read_text(encoding="utf-8"))
            except Exception:
                self._index = {}

    def _save_index(self) -> None:
        try:
            self.index_file.write_text(json.dumps(self._index, indent=2), encoding="utf-8")
        except Exception:
            pass

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        record = self._index.get(cache_key)
        if not record:
            return None
        audio_path = Path(record.get("file_path", ""))
        if not audio_path.exists():
            return None
        return record

    def put(self, cache_key: str, record: Dict[str, Any]) -> None:
        self._index[cache_key] = record
        self._save_index()
