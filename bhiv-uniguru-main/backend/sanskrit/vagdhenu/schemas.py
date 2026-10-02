"""Schemas and contracts for Vāgdhenu Sanskrit Chanting TTS."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class MeterAnalysis(BaseModel):
    detected_meter: Optional[str] = Field(default=None, description="Name of detected Sanskrit meter (vṛtta)")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    syllable_count: int = Field(default=0)
    pada_syllable_counts: List[int] = Field(default_factory=list)
    laghu_guru_pattern: str = Field(default="")
    meter_description: Optional[str] = None

    @property
    def meter_name(self) -> str:
        return self.detected_meter or "Unknown"


class ChantRequest(BaseModel):
    text: str = Field(..., min_length=2, max_length=1500, description="Sanskrit shloka in Devanagari or IAST")
    meter: Optional[str] = Field(default=None, description="Explicit meter override (e.g. Anustubh, Indravajra)")
    reference_audio: Optional[str] = Field(default=None, description="Optional path or URI to reference chanting audio")

    @field_validator("text")
    @classmethod
    def _validate_and_strip(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Sanskrit text must not be empty.")
        return stripped


class AudioMetadata(BaseModel):
    audio_id: str
    file_format: str = "wav"
    duration: Optional[float] = None
    file_size_bytes: int = 0
    created_at: str
    text_hash: str
    meter: Optional[str] = None
    sample_rate: int = 24000
    channels: int = 1

    @property
    def duration_seconds(self) -> float:
        return self.duration or 0.0


class ChantResponse(BaseModel):
    success: bool
    text: str
    meter: Optional[Any] = None
    audio_id: Optional[str] = None
    audio_url: Optional[str] = None
    duration: Optional[float] = None
    available: bool = True
    reason: Optional[str] = None
    cached: bool = False
    engine: str = "Vāgdhenu TTS"
    metadata: Optional[AudioMetadata] = None
    meter_analysis: Optional[MeterAnalysis] = None

