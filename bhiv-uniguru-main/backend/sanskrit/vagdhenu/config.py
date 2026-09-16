"""Vāgdhenu Sanskrit Chanting TTS Configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


_CURR = Path(__file__).resolve()
ROOT = _CURR.parents[3]
AUDIO_CACHE_DIR = ROOT / "backend" / "data" / "audio" / "vagdhenu"


class VagdhenuConfig(BaseModel):
    enabled: bool = Field(default=True)
    device: str = Field(default_factory=lambda: os.getenv("VAGDHENU_DEVICE", "cpu"))
    model_path: Optional[str] = Field(default_factory=lambda: os.getenv("VAGDHENU_MODEL_PATH", None))
    api_url: Optional[str] = Field(default_factory=lambda: os.getenv("VAGDHENU_API_URL", None))
    hf_space: str = Field(default="prathoshap/vagdhenu-demo")
    audio_cache_dir: Path = Field(default=AUDIO_CACHE_DIR)
    max_text_chars: int = Field(default=1000)
    sample_rate: int = Field(default=24000)
    audio_format: str = Field(default="wav")
    timeout_seconds: float = Field(default=30.0)
    mock_mode: bool = Field(
        default_factory=lambda: os.getenv("VAGDHENU_MOCK_MODE", "true").lower() in {"1", "true", "yes"}
    )
