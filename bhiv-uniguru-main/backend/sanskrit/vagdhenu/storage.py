"""Audio Storage abstraction for generated Sanskrit Chants."""

from __future__ import annotations

import io
import json
import os
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .exceptions import AudioStorageError
from .schemas import AudioMetadata

_CURR = Path(__file__).resolve()
ROOT = _CURR.parents[3]
DEFAULT_STORAGE_DIR = ROOT / "backend" / "data" / "audio" / "chants"


def _calculate_wav_duration(audio_bytes: bytes) -> Optional[float]:
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate > 0:
                return round(frames / float(rate), 2)
    except Exception:
        pass
    return None


class AudioStorage:
    def __init__(self, storage_dir: Optional[Path] = None, cache_dir: Optional[Path] = None) -> None:
        self.storage_dir = Path(storage_dir or cache_dir or DEFAULT_STORAGE_DIR)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.storage_dir / "audio_manifest.json"
        self._manifest: Dict[str, Dict[str, Any]] = {}
        self._load_manifest()

    def _load_manifest(self) -> None:
        if self.metadata_file.exists():
            try:
                self._manifest = json.loads(self.metadata_file.read_text(encoding="utf-8"))
            except Exception:
                self._manifest = {}

    def _save_manifest(self) -> None:
        try:
            self.metadata_file.write_text(json.dumps(self._manifest, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _safe_path(self, audio_id: str, ext: str = "wav") -> Path:
        if ".." in audio_id or "/" in audio_id or "\\" in audio_id:
            raise ValueError("Path traversal detected in audio_id.")
        clean_id = os.path.basename(audio_id)
        if not clean_id.endswith(f".{ext}"):
            clean_id = f"{clean_id}.{ext}"
        return self.storage_dir / clean_id

    def save(
        self,
        audio_bytes: bytes,
        audio_id: str,
        file_format: str = "wav",
        text_hash: str = "",
        meter: Optional[str] = None,
        duration: Optional[float] = None,
    ) -> AudioMetadata:
        if not audio_bytes:
            raise AudioStorageError("Cannot save empty audio bytes.")

        target_file = self._safe_path(audio_id, ext=file_format)
        target_file.write_bytes(audio_bytes)

        if duration is None and file_format == "wav":
            duration = _calculate_wav_duration(audio_bytes)

        meta = AudioMetadata(
            audio_id=audio_id,
            file_format=file_format,
            duration=duration,
            file_size_bytes=len(audio_bytes),
            created_at=datetime.now(timezone.utc).isoformat(),
            text_hash=text_hash,
            meter=meter,
        )

        self._manifest[audio_id] = meta.model_dump()
        self._save_manifest()
        return meta

    def save_audio(
        self,
        audio_id: str,
        audio_bytes: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AudioMetadata:
        meta_dict = metadata or {}
        return self.save(
            audio_bytes=audio_bytes,
            audio_id=audio_id,
            file_format=meta_dict.get("format", "wav"),
            text_hash=meta_dict.get("text_hash", ""),
            meter=meta_dict.get("meter"),
            duration=meta_dict.get("duration"),
        )

    def get_path(self, audio_id: str, file_format: str = "wav", ext: Optional[str] = None) -> Optional[Path]:
        fmt = ext or file_format
        p = self._safe_path(audio_id, ext=fmt)
        if p.exists():
            return p
        return None

    def get_bytes(self, audio_id: str, file_format: str = "wav", ext: Optional[str] = None) -> Optional[Tuple[bytes, AudioMetadata]]:
        fmt = ext or file_format
        p = self.get_path(audio_id, file_format=fmt)
        if not p:
            return None
        audio_bytes = p.read_bytes()
        meta_dict = self._manifest.get(audio_id, {})
        meta = AudioMetadata(
            audio_id=audio_id,
            file_format=fmt,
            duration=meta_dict.get("duration"),
            file_size_bytes=len(audio_bytes),
            created_at=meta_dict.get("created_at", datetime.now(timezone.utc).isoformat()),
            text_hash=meta_dict.get("text_hash", ""),
            meter=meta_dict.get("meter"),
        )
        return audio_bytes, meta

    def get_audio_bytes(self, audio_id: str, file_format: str = "wav", ext: Optional[str] = None) -> Optional[bytes]:
        res = self.get_bytes(audio_id, file_format=file_format, ext=ext)
        return res[0] if res else None


    def delete(self, audio_id: str, file_format: str = "wav") -> bool:
        p = self._safe_path(audio_id, ext=file_format)
        if p.exists():
            p.unlink()
            self._manifest.pop(audio_id, None)
            self._save_manifest()
            return True
        return False
