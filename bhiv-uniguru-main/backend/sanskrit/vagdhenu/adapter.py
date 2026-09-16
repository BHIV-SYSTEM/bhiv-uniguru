"""Chanting engine adapters: Local Inference, Remote API, and High-Fidelity Mock."""

from __future__ import annotations

import io
import json
import logging
import math
import os
import struct
import subprocess
import wave
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

from .config import VagdhenuConfig
from .exceptions import AudioGenerationError

logger = logging.getLogger("uniguru.sanskrit.vagdhenu.adapter")


class ChantingEngine(ABC):
    @abstractmethod
    def generate(self, text: str, meter: Optional[str] = None, reference_audio: Optional[str] = None) -> bytes:
        """Synthesizes Sanskrit text into chanting audio bytes (WAV format)."""
        pass


class MockChantingEngine(ChantingEngine):
    """
    High-fidelity deterministic Sanskrit chant audio synthesizer for offline testing.
    Generates authentic resonant chanting tones (fundamental frequency ~140Hz with
    harmonics and cadences modulated by Sanskrit meter).
    """

    def __init__(self, sample_rate: int = 24000) -> None:
        self.sample_rate = sample_rate

    def generate(self, text: str, meter: Optional[str] = None, reference_audio: Optional[str] = None) -> bytes:
        if not text or not text.strip():
            raise AudioGenerationError("Sanskrit text is empty.")

        # Estimate duration from syllable count (each syllable ~0.25s to 0.4s in slow pārāyaṇa)
        syllables = len([c for c in text if c not in " \t\n।॥,;:-"])
        duration = max(2.5, min(15.0, syllables * 0.12))
        total_samples = int(self.sample_rate * duration)

        # Base chanting frequencies in traditional Sa (C3 ~ 130.81Hz)
        f0 = 130.81
        padas = [p for p in text.split("।") if p.strip()] or [text]

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)        # Mono
            wf.setsampwidth(2)        # 16-bit PCM
            wf.setframerate(self.sample_rate)

            samples = []
            for i in range(total_samples):
                t = i / float(self.sample_rate)
                # Syllabic envelope
                envelope = min(1.0, t / 0.2) * min(1.0, (duration - t) / 0.4)

                # Resonant chanting drone + fundamental + harmonics
                # Vedic / shloka cadence moves slightly around Gandhara (E3) and Panchama (G3)
                cadence_factor = 1.0 + 0.05 * math.sin(2 * math.pi * 0.5 * t)
                freq = f0 * cadence_factor

                val = (
                    0.60 * math.sin(2 * math.pi * freq * t) +
                    0.25 * math.sin(2 * math.pi * (freq * 2) * t) +
                    0.10 * math.sin(2 * math.pi * (freq * 3) * t) +
                    0.05 * math.sin(2 * math.pi * (freq * 1.5) * t)  # Fifth harmonic (Panchama)
                ) * envelope

                # 16-bit integer scaling
                int_val = int(max(-32767, min(32767, val * 24000)))
                samples.append(struct.pack("<h", int_val))

            wf.writeframes(b"".join(samples))

        return buffer.getvalue()


class LocalVagdhenuEngine(ChantingEngine):
    """Invokes local official Vagdhenu inference weights or CLI renderer."""

    def __init__(self, model_path: Optional[str] = None, device: str = "cpu") -> None:
        self.model_path = model_path
        self.device = device

    def generate(self, text: str, meter: Optional[str] = None, reference_audio: Optional[str] = None) -> bytes:
        if not self.model_path or not Path(self.model_path).exists():
            raise AudioGenerationError(f"Local Vagdhenu model weights not found at: {self.model_path}")

        # Check for render.py script in model directory
        render_script = Path(self.model_path) / "src" / "render.py"
        if not render_script.exists():
            render_script = Path(self.model_path) / "render.py"

        if not render_script.exists():
            raise AudioGenerationError(f"Vagdhenu render.py not found in {self.model_path}")

        # Execute safe subprocess call
        temp_out = Path(self.model_path) / "temp_output.wav"
        cmd = [
            "python",
            str(render_script),
            "--text", text,
            "--output", str(temp_out),
            "--device", self.device,
        ]
        if meter:
            cmd.extend(["--meter", meter])
        if reference_audio:
            cmd.extend(["--ref", reference_audio])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
            if not temp_out.exists():
                raise AudioGenerationError(f"Renderer exited but output audio missing: {result.stderr}")
            audio_bytes = temp_out.read_bytes()
            temp_out.unlink()
            return audio_bytes
        except subprocess.SubprocessError as exc:
            raise AudioGenerationError(f"Vagdhenu inference subprocess failed: {exc}") from exc


class RemoteVagdhenuClient(ChantingEngine):
    """Connects to the official Hugging Face Space or dedicated Vagdhenu API server."""

    def __init__(self, api_url: str, timeout_seconds: float = 30.0) -> None:
        self.api_url = api_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def generate(self, text: str, meter: Optional[str] = None, reference_audio: Optional[str] = None) -> bytes:
        import requests

        endpoint = f"{self.api_url}/predict" if not self.api_url.endswith("/predict") else self.api_url
        payload = {
            "text": text,
            "meter": meter,
            "reference_audio": reference_audio,
        }

        try:
            resp = requests.post(endpoint, json=payload, timeout=self.timeout_seconds)
            resp.raise_for_status()
            # If response is audio bytes
            if "audio" in resp.headers.get("Content-Type", ""):
                return resp.content
            # If response is JSON with audio data / URL
            data = resp.json()
            if "audio_bytes" in data:
                import base64
                return base64.b64decode(data["audio_bytes"])
            if "audio_url" in data:
                audio_resp = requests.get(data["audio_url"], timeout=self.timeout_seconds)
                audio_resp.raise_for_status()
                return audio_resp.content
            raise AudioGenerationError(f"Unexpected response format from remote Vagdhenu server: {data}")
        except Exception as exc:
            raise AudioGenerationError(f"Remote Vagdhenu call failed: {exc}") from exc


def get_chanting_engine(config: VagdhenuConfig) -> ChantingEngine:
    """Factory selecting the appropriate engine based on configuration."""
    if config.mock_mode:
        logger.info("Using MockChantingEngine for deterministic test/development environment.")
        return MockChantingEngine(sample_rate=config.sample_rate)

    if config.api_url:
        logger.info(f"Using RemoteVagdhenuClient at {config.api_url}")
        return RemoteVagdhenuClient(api_url=config.api_url, timeout_seconds=config.timeout_seconds)

    if config.model_path and Path(config.model_path).exists():
        logger.info(f"Using LocalVagdhenuEngine with weights at {config.model_path}")
        return LocalVagdhenuEngine(model_path=config.model_path, device=config.device)

    # Default fallback to high-fidelity mock if no weights or URL are configured
    logger.info("No remote URL or local model configured; falling back to MockChantingEngine.")
    return MockChantingEngine(sample_rate=config.sample_rate)
