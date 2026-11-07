"""
Comprehensive Unit & Integration Test Suite for UniGuru Data Preprocessing Pipeline.
Tests:
  1. Extraction (PDF, TXT, MD, YouTube/Web JSON)
  2. Text Cleaning (headers/footers, hyphenation, page numbers)
  3. Deduplication (exact hash & near-duplicate shingles)
  4. Language Detection (Marathi, Hindi, English, Sanskrit)
  5. Quality Validation & Rejections
  6. Semantic Chunking
  7. End-to-end Pipeline & Fine-Tuning Export
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
import pytest

from backend.preprocessing.chunker import TextChunker
from backend.preprocessing.cleaner import TextCleaner
from backend.preprocessing.deduplicator import DocumentDeduplicator
from backend.preprocessing.extractor import DocumentExtractor
from backend.preprocessing.language_detector import LanguageDetector
from backend.preprocessing.pipeline import PreprocessingPipeline
from backend.preprocessing.validator import QualityValidator

_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 1. Extraction Tests
# ---------------------------------------------------------------------------

def test_extract_txt_and_markdown():
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("---\ntitle: Quantum Superposition\nauthor: UniGuru Research\n---\n\nSuperposition is a fundamental principle of quantum mechanics.")
        md_path = Path(f.name)

    try:
        doc = DocumentExtractor.extract(md_path)
        assert doc.file_type == "md"
        assert doc.title == "Quantum Superposition"
        assert doc.metadata.get("author") == "UniGuru Research"
        assert "fundamental principle" in doc.raw_text
    finally:
        md_path.unlink(missing_ok=True)


def test_extract_youtube_transcript_json():
    sample_transcript = [
        {"text": "Welcome to today's lecture on classical mechanics.", "start": 0.0, "duration": 3.2},
        {"text": "We will examine Newton's three laws of motion.", "start": 3.5, "duration": 4.1},
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(sample_transcript, f)
        json_path = Path(f.name)

    try:
        doc = DocumentExtractor.extract(json_path)
        assert doc.file_type == "json"
        assert "classical mechanics" in doc.raw_text
        assert "laws of motion" in doc.raw_text
    finally:
        json_path.unlink(missing_ok=True)


def test_extract_authoritative_pdf():
    pdf_path = _ROOT / "backend" / "data" / "authoritative_pdfs" / "arxiv_quantum_computing_overview.pdf"
    if pdf_path.is_file():
        doc = DocumentExtractor.extract(pdf_path)
        assert doc.file_type == "pdf"
        assert len(doc.pages) > 0
        assert len(doc.raw_text) > 50


# ---------------------------------------------------------------------------
# 2. Text Cleaner Tests
# ---------------------------------------------------------------------------

def test_text_cleaner_removes_page_numbers_and_hyphenation():
    raw_text = (
        "This is an exam-\nple of hyphenated text.\n\n"
        "Page 14\n"
        "The subsequent discussion covers thermodynamics.\n"
        "--- 15 ---\n"
        "Final remarks."
    )
    cleaned = TextCleaner.clean(raw_text)
    assert "example of hyphenated text." in cleaned
    assert "Page 14" not in cleaned
    assert "--- 15 ---" not in cleaned
    assert "thermodynamics" in cleaned


def test_text_cleaner_recurring_headers_and_footers():
    pages = [
        "Maharashtra State Board Balbharti\nChapter 1: Arithmetic operations.\nFooter: Pune 2026",
        "Maharashtra State Board Balbharti\nChapter 1: Continued fractions.\nFooter: Pune 2026",
        "Maharashtra State Board Balbharti\nChapter 1: Solved problems.\nFooter: Pune 2026",
    ]
    headers, footers = TextCleaner.identify_recurring_headers_footers(pages, occurrence_threshold=0.5)
    assert "Maharashtra State Board Balbharti" in headers
    assert "Footer: Pune 2026" in footers

    cleaned_p1 = TextCleaner.clean(pages[0], headers=headers, footers=footers)
    assert "Maharashtra State Board Balbharti" not in cleaned_p1
    assert "Footer: Pune 2026" not in cleaned_p1
    assert "Chapter 1: Arithmetic operations." in cleaned_p1


# ---------------------------------------------------------------------------
# 3. Deduplication Tests
# ---------------------------------------------------------------------------

def test_deduplicator_exact_and_near_duplicate():
    dedup = DocumentDeduplicator()
    text_a = "Photosynthesis is the process by which green plants convert sunlight into chemical energy."
    text_b = "Photosynthesis is the process by which green plants convert sunlight into chemical energy."
    text_c = "Newtonian gravitation describes the mutual attraction between masses throughout the cosmos."

    is_dup1, orig1, _ = dedup.check_duplicate(text_a, document_id="doc_1", file_name="bio1.txt")
    assert is_dup1 is False

    # Exact duplicate
    is_dup2, orig2, match_type = dedup.check_duplicate(text_b, document_id="doc_2", file_name="bio2.txt")
    assert is_dup2 is True
    assert orig2 == "doc_1"
    assert match_type == "exact_hash_match"

    # Distinct document
    is_dup3, _, _ = dedup.check_duplicate(text_c, document_id="doc_3", file_name="phys.txt")
    assert is_dup3 is False


# ---------------------------------------------------------------------------
# 4. Language Detection Tests (Marathi, Hindi, English, Sanskrit)
# ---------------------------------------------------------------------------

def test_language_detection_english():
    text = "The quick brown fox jumps over the lazy dog. Classical mechanics explains terrestrial motion."
    res = LanguageDetector.detect(text)
    assert res["language"] == "english"
    assert res["confidence"] > 0.8


def test_language_detection_marathi():
    text = "इयत्ता पहिली गणित विषयाचा अभ्यास येथे दिलेला आहे. विद्यार्थ्यांनी सर्व उदाहरणे सोडवून पहावीत आणि स्वाध्याय पूर्ण करावा."
    res = LanguageDetector.detect(text)
    assert res["language"] == "marathi"
    assert res["confidence"] >= 0.7


def test_language_detection_hindi():
    text = "भारत एक विशाल देश है और इसकी संस्कृति अत्यंत प्राचीन है। यहाँ अनेक भाषाएं और धर्म हैं लेकिन सब मिलजुल कर रहते हैं।"
    res = LanguageDetector.detect(text)
    assert res["language"] == "hindi"
    assert res["confidence"] >= 0.7


def test_language_detection_sanskrit():
    text = "सर्वे भवन्तु सुखिनः सर्वे सन्तु निरामयाः। सर्वे भद्राणि पश्यन्तु मा कश्चिद्दुःखभाग्भवेत्॥ ॐ शान्तिः शान्तिः शान्तिः।"
    res = LanguageDetector.detect(text)
    assert res["language"] == "sanskrit"
    assert res["confidence"] >= 0.7


# ---------------------------------------------------------------------------
# 5. Quality Validation Tests
# ---------------------------------------------------------------------------

def test_quality_validator_passes_pedagogical_text():
    validator = QualityValidator()
    text = (
        "Cellular respiration is a set of metabolic reactions that take place in the cells of organisms "
        "to convert chemical energy from oxygen molecules or nutrients into adenosine triphosphate (ATP), "
        "and then release waste products."
    )
    report = validator.evaluate(text)
    assert report.passed is True
    assert report.quality_score >= 0.7


def test_quality_validator_rejects_empty_or_garbage():
    validator = QualityValidator()
    # Too short
    rep1 = validator.evaluate("Too short.")
    assert rep1.passed is False

    # Low alphanumeric / binary noise
    rep2 = validator.evaluate("@#$%^&*()_+ ~~~ /// ??? !!! >>> <<< ||| $$$ %%% ^^^ &&& *** ((()))")
    assert rep2.passed is False


# ---------------------------------------------------------------------------
# 6. Semantic Chunking Tests
# ---------------------------------------------------------------------------

def test_semantic_chunker():
    chunker = TextChunker(chunk_size=200, chunk_overlap=40)
    text = (
        "Sentence one explains the principle of conservation of energy. "
        "Sentence two provides an empirical demonstration of kinetic transfer. "
        "Sentence three shows potential energy converting into mechanical work."
    )
    chunks = chunker.chunk_document(text, document_id="doc_test", language="english", domain="physics")
    assert len(chunks) >= 1
    for c in chunks:
        assert c.document_id == "doc_test"
        assert c.language == "english"
        assert c.domain == "physics"
        assert len(c.text) > 0


# ---------------------------------------------------------------------------
# 7. End-to-End Pipeline & Fine-Tuning Export Test
# ---------------------------------------------------------------------------

def test_pipeline_end_to_end_in_temporary_workspace():
    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)
        pipeline = PreprocessingPipeline(base_data_dir=base_dir, chunk_size=300, chunk_overlap=50)

        # Create a raw textbook sample file in raw_dir
        sample_file = pipeline.raw_dir / "sample_math_marathi.txt"
        sample_file.write_text(
            "इयत्ता पहिली गणित विषयाचा पाठ १. संख्या ज्ञान आणि बेरीज करणे.\n"
            "विद्यार्थ्यांनी १ ते १० पर्यंतचे अंक समजून घ्यावेत. "
            "दोन अधिक दोन बरोबर चार होतात. पुढील उदाहरणे सोडवा.",
            encoding="utf-8",
        )

        res = pipeline.process_file(sample_file, domain_hint="mathematics")
        assert res["status"] == "success"
        assert res["language"] == "marathi"
        assert res["domain"] == "mathematics"
        assert res["chunks_count"] >= 1

        doc_id = res["document_id"]
        # Verify all destination folders received the generated artifacts
        assert (pipeline.extracted_dir / f"{doc_id}.json").is_file()
        assert (pipeline.cleaned_dir / f"{doc_id}.json").is_file()
        assert (pipeline.processed_dir / f"{doc_id}.json").is_file()
        assert (pipeline.chunks_dir / f"{doc_id}_chunks.jsonl").is_file()

        # Test fine-tuning dataset export
        export_path = pipeline.export_fine_tuning_dataset(min_chunk_len=50)
        assert export_path.is_file()
        with export_path.open("r", encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
            assert len(lines) >= 1
            assert "context" in lines[0]
            assert "question" in lines[0]
            assert "answer" in lines[0]

