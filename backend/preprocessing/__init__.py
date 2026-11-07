"""
UniGuru Data Collection & Preprocessing Subsystem.
Modular ingestion pipeline for Authoritative Textbooks, PDFs, DOCX, Transcripts,
with multi-stage cleaning, deduplication, language detection (Marathi, Hindi, English, Sanskrit),
quality validation, semantic chunking, and fine-tuning dataset export.
"""
from __future__ import annotations

from backend.preprocessing.extractor import DocumentExtractor, ExtractedDocument
from backend.preprocessing.cleaner import TextCleaner
from backend.preprocessing.deduplicator import DocumentDeduplicator
from backend.preprocessing.language_detector import LanguageDetector
from backend.preprocessing.validator import QualityValidator, QualityReport
from backend.preprocessing.chunker import TextChunker, TextChunk
from backend.preprocessing.pipeline import PreprocessingPipeline

__all__ = [
    "DocumentExtractor",
    "ExtractedDocument",
    "TextCleaner",
    "DocumentDeduplicator",
    "LanguageDetector",
    "QualityValidator",
    "QualityReport",
    "TextChunker",
    "TextChunk",
    "PreprocessingPipeline",
]

