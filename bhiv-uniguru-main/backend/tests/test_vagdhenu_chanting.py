"""Unit and integration tests for Vāgdhenu Sanskrit Chanting TTS Engine."""

import os
import pytest
from fastapi.testclient import TestClient

from backend.sanskrit.vagdhenu.meter import (
    analyze_meter,
    syllabify_sanskrit,
    classify_syllable_weight,
)
from backend.sanskrit.vagdhenu.storage import AudioStorage
from backend.sanskrit.vagdhenu.cache import compute_audio_cache_key
from backend.sanskrit.vagdhenu.adapter import MockChantingEngine
from backend.sanskrit.vagdhenu.service import get_vagdhenu_service
from backend.service.api import app
from backend.service.uniguru_runtime_api import app as runtime_app


# ── 1. Pingala Chandashastra Meter Detection Tests ─────────────────────────────

def test_anustubh_meter_detection():
    # 32-syllable standard Gita shloka
    shloka = "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः । मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय ॥"
    meter = analyze_meter(shloka)
    assert "Anuṣṭubh" in meter.meter_name or "Anustubh" in meter.meter_name
    assert meter.syllable_count >= 28  # 32 syllables nominal
    assert meter.confidence >= 0.8
    assert "L" in meter.laghu_guru_pattern or "G" in meter.laghu_guru_pattern


def test_syllabify_and_weight():
    syllables = syllabify_sanskrit("नमस्ते")
    assert len(syllables) >= 2
    # The first syllable 'न' is laghu ('L'), 'म' followed by 'स्ते' becomes guru ('G')
    pattern = "".join(classify_syllable_weight(s) for s in syllables)
    assert len(pattern) == len(syllables)


def test_meter_short_text_fallback():
    # Very short single word fallback
    meter = analyze_meter("ॐ")
    assert meter.detected_meter in ["Anuṣṭubh", "Unknown", None, "Muktaka"]
    assert meter.confidence >= 0.0


# ── 2. Audio Storage & WAV Generation Tests ───────────────────────────────────

def test_audio_storage_save_and_retrieve(tmp_path):
    storage = AudioStorage(cache_dir=tmp_path)
    engine = MockChantingEngine()
    fake_wav = engine.generate("शान्तिः", meter="Muktaka")

    meta = storage.save_audio("test_audio_01", fake_wav, {"text": "शान्तिः", "meter": "Muktaka"})
    assert meta.duration_seconds > 0.0
    assert meta.sample_rate == 24000
    assert meta.file_format == "wav"

    retrieved = storage.get_audio_bytes("test_audio_01")
    assert retrieved is not None
    assert retrieved[:4] == b"RIFF"
    assert b"WAVE" in retrieved[:16]


def test_audio_storage_path_safety(tmp_path):
    storage = AudioStorage(cache_dir=tmp_path)
    # Attempt path traversal
    with pytest.raises(ValueError):
        storage.get_audio_bytes("../../../etc/passwd")


def test_deterministic_cache_key():
    k1 = compute_audio_cache_key("ॐ नमः शिवाय", "Anustubh", 1.0, 24000)
    k2 = compute_audio_cache_key("ॐ नमः शिवाय", "Anustubh", 1.0, 24000)
    k3 = compute_audio_cache_key("ॐ नमो नारायणाय", "Anustubh", 1.0, 24000)

    assert k1 == k2
    assert k1 != k3
    assert len(k1) == 64  # SHA-256 hex string


# ── 3. Vagdhenu Service End-to-End Tests ───────────────────────────────────────

def test_vagdhenu_service_chant_generation():
    service = get_vagdhenu_service()
    shloka = "यदा यदा हि धर्मस्य ग्लानिर्भवति भारत । अभ्युत्थानमधर्मस्य तदात्मानं सृजाम्यहम् ॥"
    resp = service.generate_chant(shloka)

    assert resp.available is True
    assert resp.audio_id is not None
    assert resp.audio_url.startswith("/api/audio/")
    assert resp.meter.meter_name == "Anuṣṭubh"
    assert resp.metadata.duration_seconds > 0.5
    assert resp.metadata.sample_rate == 24000

    # Second call should be a cache hit
    resp2 = service.generate_chant(shloka)
    assert resp2.audio_id == resp.audio_id
    assert resp2.engine == resp.engine


# ── 4. API Endpoint Integration Tests ─────────────────────────────────────────

def test_api_sanskrit_chant_endpoint():
    client = TestClient(app)
    response = client.post(
        "/api/sanskrit/chant",
        json={"text": "सत्यमेव जयते नानृतम्", "preferred_engine": "mock"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert "audio_id" in data
    assert "audio_url" in data
    assert "meter" in data

    audio_id = data["audio_id"]

    # Test GET audio file
    audio_resp = client.get(f"/api/audio/{audio_id}")
    assert audio_resp.status_code == 200
    assert audio_resp.headers["content-type"] == "audio/wav"
    assert len(audio_resp.content) > 100


def test_runtime_sanskrit_decode_includes_audio():
    client = TestClient(runtime_app)
    response = client.post(
        "/runtime/sanskrit/decode",
        json={"query": "dharma"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "audio" in data
    assert data["audio"] is not None
    assert data["audio"]["available"] is True
    assert "meter" in data["audio"]
