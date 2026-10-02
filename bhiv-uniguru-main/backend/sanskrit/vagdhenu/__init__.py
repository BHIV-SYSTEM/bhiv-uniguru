"""Vāgdhenu Sanskrit Chanting TTS integration package."""

from .config import VagdhenuConfig
from .schemas import ChantRequest, ChantResponse, MeterAnalysis, AudioMetadata
from .meter import detect_sanskrit_meter, normalize_sanskrit
from .storage import AudioStorage
from .cache import VagdhenuAudioCache
from .adapter import ChantingEngine, MockChantingEngine, LocalVagdhenuEngine, RemoteVagdhenuClient
from .service import VagdhenuService, get_vagdhenu_service

__all__ = [
    "VagdhenuConfig",
    "ChantRequest",
    "ChantResponse",
    "MeterAnalysis",
    "AudioMetadata",
    "detect_sanskrit_meter",
    "normalize_sanskrit",
    "AudioStorage",
    "VagdhenuAudioCache",
    "ChantingEngine",
    "MockChantingEngine",
    "LocalVagdhenuEngine",
    "RemoteVagdhenuClient",
    "VagdhenuService",
    "get_vagdhenu_service",
]
