"""Custom exceptions for Vāgdhenu Sanskrit Chanting TTS."""

from __future__ import annotations


class VagdhenuError(Exception):
    """Base exception for all Vagdhenu operations."""
    pass


class MeterDetectionError(VagdhenuError):
    """Raised when Sanskrit meter detection fails critically."""
    pass


class AudioGenerationError(VagdhenuError):
    """Raised when audio synthesis fails."""
    pass


class AudioStorageError(VagdhenuError):
    """Raised when saving or retrieving generated audio fails."""
    pass
