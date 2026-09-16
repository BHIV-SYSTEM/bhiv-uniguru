from __future__ import annotations

import hashlib
import json
import os
import wave
from dataclasses import asdict, dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional


class STTUnavailableError(RuntimeError):
    """Raised when no local STT provider is configured for runtime use."""


@dataclass(frozen=True)
class AudioMetadata:
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    duration_seconds: Optional[float] = None
    sample_rate_hz: Optional[int] = None
    channels: Optional[int] = None


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str
    confidence: float
    provider: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["confidence"] = round(float(self.confidence), 4)
        return payload


class _BaseSTTProvider:
    name = "base"

    def transcribe(
        self,
        audio_bytes: bytes,
        metadata: AudioMetadata,
        hinted_language: Optional[str] = None,
    ) -> TranscriptionResult:
        raise NotImplementedError


class _ManifestSTTProvider(_BaseSTTProvider):
    name = "manifest"

    def __init__(self, manifest_path: Optional[str]) -> None:
        self._manifest_path = Path(manifest_path).expanduser() if manifest_path else None
        self._entries = self._load_entries()

    def _load_entries(self) -> Dict[str, Dict[str, Any]]:
        if not self._manifest_path or not self._manifest_path.exists():
            return {}
        with self._manifest_path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        entries = raw.get("audio_fingerprints", raw)
        if not isinstance(entries, dict):
            return {}
        return {str(key): dict(value) for key, value in entries.items()}

    def transcribe(
        self,
        audio_bytes: bytes,
        metadata: AudioMetadata,
        hinted_language: Optional[str] = None,
    ) -> TranscriptionResult:
        key_candidates = [metadata.sha256, metadata.filename]
        for key in key_candidates:
            if key not in self._entries:
                continue
            entry = self._entries[key]
            text = str(entry.get("text") or "").strip()
            if not text:
                break
            language = str(entry.get("language") or hinted_language or "en").strip().lower()
            confidence = float(entry.get("confidence", 0.0) or 0.0)
            return TranscriptionResult(
                text=text,
                language=language,
                confidence=confidence,
                provider=self.name,
                metadata={
                    "matched_on": key,
                    "audio": asdict(metadata),
                },
            )
        raise STTUnavailableError(
            "No matching local transcription was found. Configure a local model path or extend the STT manifest."
        )


class _TransformersSTTProvider(_BaseSTTProvider):
    """
    Local inference provider using HuggingFace Transformers.
    Targeted at indigenous Indic models (AI4Bharat, BharatGen).
    """
    name = "transformers-local"

    def __init__(self, model_path: str) -> None:
        self._model_path = model_path
        self._pipeline = None

    def _load_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline
        try:
            from transformers import pipeline
        except ImportError as exc:
            raise STTUnavailableError(
                "transformers/torch are not installed. "
                "Run 'pip install transformers torch' to enable local indigenous ASR models."
            ) from exc
        
        # Load ASR pipeline using local weights
        self._pipeline = pipeline(
            task="automatic-speech-recognition",
            model=self._model_path,
            tokenizer=self._model_path,
            feature_extractor=self._model_path,
            return_timestamps=False, # Standard for query transcription
        )
        return self._pipeline

    def transcribe(
        self,
        audio_bytes: bytes,
        metadata: AudioMetadata,
        hinted_language: Optional[str] = None,
    ) -> TranscriptionResult:
        pipe = self._load_pipeline()
        
        # In actual production with Whisper-based models (e.g., IndicWhisper), 
        # the model can auto-detect language if not hinted.
        generate_kwargs = {}
        if hinted_language:
            generate_kwargs["language"] = hinted_language
            
        result = pipe(audio_bytes, generate_kwargs=generate_kwargs)
        
        text = str(result.get("text") or "").strip()
        if not text:
            raise STTUnavailableError("The local indigenous STT model returned an empty transcription.")
            
        # Extract metadata if provided by the model (e.g. detected language)
        detected_language = result.get("chunks", [{}])[0].get("language") if "chunks" in result else None
        
        return TranscriptionResult(
            text=text,
            language=str(detected_language or hinted_language or "en").strip().lower(),
            confidence=float(result.get("confidence", 0.0) or 0.0),
            provider=self.name,
            metadata={
                "model_path": self._model_path,
                "audio": asdict(metadata),
                "is_indigenous": True,
                "framework": "transformers",
            },
        )


class STTEngine:
    """
    Local speech-to-text boundary for UniGuru.

    Production mode expects a local model snapshot to be mounted on disk.
    CI and development can use a deterministic manifest for stable tests.
    """

    def __init__(
        self,
        provider_name: Optional[str] = None,
        model_path: Optional[str] = None,
        manifest_path: Optional[str] = None,
    ) -> None:
        provider_name = (provider_name or os.getenv("UNIGURU_STT_PROVIDER", "manifest")).strip().lower()
        model_path = model_path or os.getenv("UNIGURU_STT_MODEL_PATH", "").strip()
        default_manifest = Path(__file__).with_name("sample_manifest.json")
        manifest_path = manifest_path or os.getenv("UNIGURU_STT_MANIFEST_PATH", "").strip() or str(default_manifest)

        if provider_name == "transformers":
            if not model_path:
                raise STTUnavailableError(
                    "UNIGURU_STT_MODEL_PATH must point to a local ASR snapshot when UNIGURU_STT_PROVIDER=transformers."
                )
            self.provider = _TransformersSTTProvider(model_path=model_path)
        else:
            self.provider = _ManifestSTTProvider(manifest_path=manifest_path)

    def transcribe(
        self,
        audio_bytes: bytes,
        *,
        filename: str,
        content_type: str,
        hinted_language: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not audio_bytes:
            raise ValueError("audio_bytes must not be empty.")
        metadata = self._build_audio_metadata(
            audio_bytes=audio_bytes,
            filename=filename,
            content_type=content_type,
        )
        result = self.provider.transcribe(
            audio_bytes=audio_bytes,
            metadata=metadata,
            hinted_language=hinted_language,
        )
        return result.to_dict()

    @staticmethod
    def _build_audio_metadata(audio_bytes: bytes, filename: str, content_type: str) -> AudioMetadata:
        sha256 = hashlib.sha256(audio_bytes).hexdigest()
        duration_seconds = None
        sample_rate_hz = None
        channels = None

        if content_type in {"audio/wav", "audio/x-wav", "audio/wave"} or filename.lower().endswith(".wav"):
            try:
                with wave.open(BytesIO(audio_bytes), "rb") as wav_file:
                    frames = wav_file.getnframes()
                    sample_rate_hz = wav_file.getframerate()
                    channels = wav_file.getnchannels()
                    if sample_rate_hz:
                        duration_seconds = frames / float(sample_rate_hz)
            except (wave.Error, EOFError):
                duration_seconds = None

        return AudioMetadata(
            filename=filename,
            content_type=content_type or "application/octet-stream",
            size_bytes=len(audio_bytes),
            sha256=sha256,
            duration_seconds=duration_seconds,
            sample_rate_hz=sample_rate_hz,
            channels=channels,
        )
