"""Vāgdhenu Sanskrit Chanting Service integrating Meter, Engine, Storage, and Caching."""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, Optional

from .adapter import ChantingEngine, get_chanting_engine
from .cache import VagdhenuAudioCache, compute_cache_key
from .config import VagdhenuConfig
from .exceptions import VagdhenuError
from .meter import detect_sanskrit_meter, normalize_sanskrit
from .schemas import AudioMetadata, ChantRequest, ChantResponse, MeterAnalysis
from .storage import AudioStorage

logger = logging.getLogger("uniguru.sanskrit.vagdhenu.service")


class VagdhenuService:
    """Core integration service orchestrating Sanskrit text analysis, chanting, storage, and caching."""

    def __init__(self, config: Optional[VagdhenuConfig] = None) -> None:
        self.config = config or VagdhenuConfig()
        self.engine: ChantingEngine = get_chanting_engine(self.config)
        self.storage = AudioStorage()
        self.cache = VagdhenuAudioCache(cache_dir=self.config.audio_cache_dir)

    def generate_chant(
        self,
        sanskrit_text: str,
        meter: Optional[str] = None,
        reference_audio: Optional[str] = None,
    ) -> ChantResponse:
        start_time = time.perf_counter()
        normalized_text = normalize_sanskrit(sanskrit_text)
        if not normalized_text:
            return ChantResponse(
                success=False,
                text=sanskrit_text,
                available=False,
                reason="Sanskrit text is empty after normalization.",
            )

        # 1. Meter Detection
        meter_analysis: Optional[MeterAnalysis] = None
        resolved_meter = meter
        if not resolved_meter:
            try:
                meter_analysis = detect_sanskrit_meter(normalized_text)
                resolved_meter = meter_analysis.detected_meter
            except Exception as exc:
                logger.warning(f"Meter detection failed: {exc}")

        # 2. Check Cache
        cache_settings = {
            "meter": resolved_meter,
            "format": self.config.audio_format,
            "sample_rate": self.config.sample_rate,
        }
        cache_key = compute_cache_key(normalized_text, meter=resolved_meter, settings=cache_settings)
        cached_record = self.cache.get(cache_key)

        if cached_record:
            audio_id = cached_record["audio_id"]
            logger.info(f"Vagdhenu cache hit for audio_id: {audio_id}")
            return ChantResponse(
                success=True,
                text=normalized_text,
                meter=meter_analysis or resolved_meter,
                audio_id=audio_id,
                audio_url=f"/api/audio/{audio_id}",
                duration=cached_record.get("duration"),
                available=True,
                cached=True,
                engine="Vāgdhenu TTS",
                metadata=AudioMetadata(
                    audio_id=audio_id,
                    duration=cached_record.get("duration"),
                    meter=resolved_meter,
                    created_at=cached_record.get("cached_at", ""),
                    text_hash="",
                ),
                meter_analysis=meter_analysis,
            )

        # 3. Audio Synthesis
        try:
            logger.info(f"Generating Sanskrit chant for meter: {resolved_meter}...")
            audio_bytes = self.engine.generate(
                text=normalized_text,
                meter=resolved_meter,
                reference_audio=reference_audio,
            )

            # Generate unique deterministic audio ID
            audio_hash = hashlib.sha256(audio_bytes).hexdigest()[:16]
            audio_id = f"chant_{audio_hash}"

            # 4. Save to Audio Storage
            meta = self.storage.save(
                audio_bytes=audio_bytes,
                audio_id=audio_id,
                file_format=self.config.audio_format,
                text_hash=cache_key,
                meter=resolved_meter,
            )

            # 5. Cache Record
            record = {
                "audio_id": audio_id,
                "file_path": str(self.storage.get_path(audio_id, ext=self.config.audio_format)),
                "duration": meta.duration,
                "meter": resolved_meter,
                "cached_at": meta.created_at,
            }
            self.cache.put(cache_key, record)

            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.info(f"Vagdhenu chant generated in {latency_ms:.2f}ms (ID: {audio_id})")

            return ChantResponse(
                success=True,
                text=normalized_text,
                meter=meter_analysis or resolved_meter,
                audio_id=audio_id,
                audio_url=f"/api/audio/{audio_id}",
                duration=meta.duration,
                available=True,
                cached=False,
                engine="Vāgdhenu TTS",
                metadata=meta,
                meter_analysis=meter_analysis,
            )
        except Exception as exc:
            logger.error(f"Vagdhenu chant generation failed: {exc}", exc_info=True)
            return ChantResponse(
                success=False,
                text=normalized_text,
                meter=resolved_meter,
                available=False,
                reason=f"AUDIO_GENERATION_FAILED: {str(exc)}",
                cached=False,
                meter_analysis=meter_analysis,
            )


_VAGDHENU_SERVICE_INSTANCE: Optional[VagdhenuService] = None


def get_vagdhenu_service() -> VagdhenuService:
    global _VAGDHENU_SERVICE_INSTANCE
    if _VAGDHENU_SERVICE_INSTANCE is None:
        _VAGDHENU_SERVICE_INSTANCE = VagdhenuService()
    return _VAGDHENU_SERVICE_INSTANCE
