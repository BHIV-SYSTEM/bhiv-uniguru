"""Staging-index tests grounded in text extracted from local Balbharati PDFs."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
from pathlib import Path
from typing import Any, List

import fitz
import numpy as np

from backend.RAG.new_rag_query import NewRAGEngine
from backend.retrieval.balbharati.chunker import HierarchicalChunker
from backend.scripts.build_balbharati_staging import (
    CachedPDFExtractor,
    _build_index,
    _sha_text,
    build_staging_index,
    extract_verified_metadata,
    validate_staging_index,
)
from backend.scripts.ingest_knowledge import TextChunker


BACKEND = Path(__file__).resolve().parents[1]
CLASS1_ENGLISH = BACKEND / "knowledge" / "balbharti" / "class_1" / "english" / "103050001.pdf"
CLASS5_EVS = BACKEND / "knowledge" / "balbharti" / "class_5" / "history" / "501000542.pdf"

BALBHARATI_RETRIEVAL_CASES = [
    {"query": "In Chapter IV A, which article sets out fundamental duties?", "expected_source": "Balbharati", "expected_document": "103050001.pdf", "expected_chapter": "Fundamental Duties", "expected_page": 5, "expected_answer_evidence": "ARTICLE 51A"},
    {"query": "What must citizens respect with the Constitution?", "expected_source": "Balbharati", "expected_document": "103050001.pdf", "expected_chapter": "Fundamental Duties", "expected_page": 5, "expected_answer_evidence": "the National Flag and the National Anthem"},
    {"query": "Which ideals should citizens cherish and follow?", "expected_source": "Balbharati", "expected_document": "103050001.pdf", "expected_chapter": "Fundamental Duties", "expected_page": 5, "expected_answer_evidence": "noble ideals which inspired our national struggle for freedom"},
    {"query": "What should citizens protect about India's sovereignty?", "expected_source": "Balbharati", "expected_document": "103050001.pdf", "expected_chapter": "Fundamental Duties", "expected_page": 5, "expected_answer_evidence": "sovereignty, unity and integrity of India"},
    {"query": "When should citizens render national service?", "expected_source": "Balbharati", "expected_document": "103050001.pdf", "expected_chapter": "Fundamental Duties", "expected_page": 5, "expected_answer_evidence": "render national service when called upon to do"},
    {"query": "What duty concerns brotherhood across India's diversities?", "expected_source": "Balbharati", "expected_document": "103050001.pdf", "expected_chapter": "Fundamental Duties", "expected_page": 5, "expected_answer_evidence": "common brotherhood amongst all the people of India"},
    {"query": "What practices should be renounced to protect women's dignity?", "expected_source": "Balbharati", "expected_document": "103050001.pdf", "expected_chapter": "Fundamental Duties", "expected_page": 5, "expected_answer_evidence": "derogatory to the dignity of women"},
    {"query": "What does the textbook say about India's composite culture?", "expected_source": "Balbharati", "expected_document": "103050001.pdf", "expected_chapter": "Fundamental Duties", "expected_page": 5, "expected_answer_evidence": "rich heritage of our composite culture"},
    {"query": "Which natural features are named in the environmental duty?", "expected_source": "Balbharati", "expected_document": "103050001.pdf", "expected_chapter": "Fundamental Duties", "expected_page": 5, "expected_answer_evidence": "forests, lakes, rivers and wild life"},
    {"query": "What does the passage say about compassion for living creatures?", "expected_source": "Balbharati", "expected_document": "103050001.pdf", "expected_chapter": "Fundamental Duties", "expected_page": 5, "expected_answer_evidence": "compassion for living creatures"},
    {"query": "Which duty mentions scientific temper and inquiry?", "expected_source": "Balbharati", "expected_document": "103050001.pdf", "expected_chapter": "Fundamental Duties", "expected_page": 5, "expected_answer_evidence": "scientific temper, humanism and the spirit of inquiry and reform"},
    {"query": "What should citizens do about public property and violence?", "expected_source": "Balbharati", "expected_document": "103050001.pdf", "expected_chapter": "Fundamental Duties", "expected_page": 5, "expected_answer_evidence": "safeguard public property and to abjure violence"},
    {"query": "What should citizens strive for in individual and collective activity?", "expected_source": "Balbharati", "expected_document": "103050001.pdf", "expected_chapter": "Fundamental Duties", "expected_page": 5, "expected_answer_evidence": "strive towards excellence"},
    {"query": "What education opportunity should parents provide to children?", "expected_source": "Balbharati", "expected_document": "103050001.pdf", "expected_chapter": "Fundamental Duties", "expected_page": 5, "expected_answer_evidence": "between the age of six and fourteen years"},
    {"query": "What form of republic does the Preamble establish?", "expected_source": "Balbharati", "expected_document": "103050001.pdf", "expected_chapter": "Fundamental Duties", "expected_page": 5, "expected_answer_evidence": "DEMOCRATIC"},
    {"query": "According to the Preamble, what kinds of justice are secured?", "expected_source": "Balbharati", "expected_document": "103050001.pdf", "expected_chapter": "Fundamental Duties", "expected_page": 5, "expected_answer_evidence": "JUSTICE, social, economic and political"},
    {"query": "What freedoms are listed under liberty in the Preamble?", "expected_source": "Balbharati", "expected_document": "103050001.pdf", "expected_chapter": "Fundamental Duties", "expected_page": 5, "expected_answer_evidence": "LIBERTY of thought"},
    {"query": "What does the Preamble state about equality?", "expected_source": "Balbharati", "expected_document": "103050001.pdf", "expected_chapter": "Fundamental Duties", "expected_page": 5, "expected_answer_evidence": "EQUALITY of status"},
    {"query": "What does fraternity assure according to the Preamble?", "expected_source": "Balbharati", "expected_document": "103050001.pdf", "expected_chapter": "Fundamental Duties", "expected_page": 5, "expected_answer_evidence": "FRATERNITY assuring the dignity"},
    {"query": "What date does the Preamble give for adopting the Constitution?", "expected_source": "Balbharati", "expected_document": "103050001.pdf", "expected_chapter": "Fundamental Duties", "expected_page": 5, "expected_answer_evidence": "twenty-sixth day of November, 1949"},
    {"query": "इयत्ता पाचवी मूलभूत कर्तव्ये: राष्ट्रध्वजाचा आदर कसा करावा?", "expected_source": "Balbharati", "expected_document": "501000542.pdf", "expected_chapter": None, "expected_page": 2, "expected_answer_evidence": "राष्ट्रध्वज"},
    {"query": "इयत्ता पाचवी मूलभूत कर्तव्ये: सार्वभौमत्व आणि एकता", "expected_source": "Balbharati", "expected_document": "501000542.pdf", "expected_chapter": None, "expected_page": 2, "expected_answer_evidence": "सार्वभौमत्व, एकता"},
    {"query": "इयत्ता पाचवी मूलभूत कर्तव्ये: नैसर्गिक पर्यावरण", "expected_source": "Balbharati", "expected_document": "501000542.pdf", "expected_chapter": None, "expected_page": 2, "expected_answer_evidence": "नैसर्गिक पर्यावरणाचे"},
    {"query": "इयत्ता पाचवी मूलभूत कर्तव्ये: वैज्ञानिक दृष्ी", "expected_source": "Balbharati", "expected_document": "501000542.pdf", "expected_chapter": None, "expected_page": 2, "expected_answer_evidence": "वैज्ञानिक दृष्ी"},
    {"query": "इयत्ता पाचवी मूलभूत कर्तव्ये: सार्वजनिक मालमत्ते", "expected_source": "Balbharati", "expected_document": "501000542.pdf", "expected_chapter": None, "expected_page": 2, "expected_answer_evidence": "सार्वजनिक मालमत्ते"},
]


def _native_page(path: Path, page_number: int) -> str:
    with fitz.open(path) as document:
        return document[page_number - 1].get_text("text")


def _ocr_page_record(document_id: str, page_number: int, text: str, native_count: int) -> dict[str, Any]:
    return {
        "document_id": document_id,
        "page_number": page_number,
        "text": text,
        "native_char_count": native_count,
        "char_count": len(text),
        "ocr_required": False,
        "ocr_backend": None,
        "ocr_status": "not_required",
        "page_status": "success",
        "error": None,
    }


class EvidenceEmbeddingModel:
    """Small deterministic encoder for testing ID/filter plumbing, not relevance quality."""

    def encode(self, texts: List[str], **_kwargs):
        vectors = np.zeros((len(texts), 1024), dtype=np.float32)
        for row, text in enumerate(texts):
            tokens = set(re.findall(r"[a-z0-9]+|[\u0900-\u097f]+", str(text).lower()))
            for token in tokens:
                offset = int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:4], "big") % vectors.shape[1]
                vectors[row, offset] = 1.0
            length = np.linalg.norm(vectors[row])
            if length:
                vectors[row] /= length
        return vectors


class SourcePDFExtractor:
    cache_hits = 0
    cache_misses = 4

    def __init__(self):
        class1_cover = _native_page(CLASS1_ENGLISH, 3)
        class1_content = _native_page(CLASS1_ENGLISH, 5)
        class5_content = _native_page(CLASS5_EVS, 2)
        self.pages = {
            "103050001.pdf": {
                "title": "",
                "pages": [
                    _ocr_page_record("", 3, class1_cover, len(class1_cover)),
                    _ocr_page_record("", 5, class1_content, len(class1_content)),
                ],
            },
            "501000542.pdf": {
                "title": "",
                "pages": [
                    _ocr_page_record(
                        "", 1,
                        "आपण असे घडलो (परिसर अभ्यास भाग २) इयत्ता पाचवी",
                        0,
                    ) | {"ocr_required": True, "ocr_backend": "cached-test-evidence", "ocr_status": "success"},
                    _ocr_page_record("", 2, class5_content, len(class5_content)),
                ],
            },
        }

    def extract(self, pdf_path: Path, document_id: str) -> Dict[str, Any]:
        result = self.pages[pdf_path.name]
        pages = [dict(page, document_id=document_id) for page in result["pages"]]
        return {"pages": pages, "pdf_title": result["title"]}


def test_balbharati_staging_build_and_twenty_evidence_cases(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.RAG.new_rag_query.MIN_SIMILARITY_THRESHOLD", 0.10)
    import faiss

    source_dir = tmp_path / "source"
    first = source_dir / "class_1" / "english" / "103050001.pdf"
    duplicate = source_dir / "class_3" / "marathi" / "103050001.pdf"
    fifth = source_dir / "class_5" / "history" / "501000542.pdf"
    for path in (first, duplicate, fifth):
        path.parent.mkdir(parents=True, exist_ok=True)
    first.write_bytes(b"class one English source fixture")
    duplicate.write_bytes(first.read_bytes())
    fifth.write_bytes(b"class five EVS source fixture")

    report = build_staging_index(
        source_dir=source_dir,
        staging_dir=tmp_path / "balbharati_staging",
        model=EvidenceEmbeddingModel(),
        pdf_extractor=SourcePDFExtractor(),
        chunker=TextChunker(max_words=90, overlap_words=15),
    )

    assert report["status"] == "READY_FOR_ISOLATED_RETRIEVAL_TESTS"
    assert report["source_pdf_count"] == 3
    assert report["unique_documents"] == 2
    assert report["duplicate_files_skipped"] == 1
    version_dir = Path(report["version_dir"])
    integrity = validate_staging_index(version_dir)
    assert integrity["valid"] is True
    assert integrity["chunk_rows"] == integrity["vector_count"]
    assert integrity["duplicate_chunk_ids"] == 0
    assert integrity["missing_document_records"] == 0

    with sqlite3.connect(version_dir / "balbharati_chunks.db") as connection:
        columns_before = [row[1] for row in connection.execute("PRAGMA table_info(chunks)")]

    engine = NewRAGEngine(
        db_path=version_dir / "balbharati_chunks.db",
        faiss_path=version_dir / "balbharati_index.faiss",
        model=EvidenceEmbeddingModel(),
    )
    engine.ollama = None
    engine.groq_client = None

    assert len(BALBHARATI_RETRIEVAL_CASES) >= 20
    for case in BALBHARATI_RETRIEVAL_CASES:
        class_level = "1" if case["expected_document"] == "103050001.pdf" else "5"
        subject = "English" if class_level == "1" else "EVS"
        results = engine.retrieve(
            case["query"],
            top_k=5,
            class_level=class_level,
            subject=subject,
            source=case["expected_source"],
        )
        matching = [
            result for result in results
            if case["expected_answer_evidence"].casefold() in " ".join(result["text"].split()).casefold()
        ]
        assert matching, f"No evidence for query: {case['query']}"
        result = matching[0]
        assert result["metadata"]["source"] == case["expected_source"]
        assert result["metadata"]["file_name"] == case["expected_document"]
        assert result["metadata"]["chapter"] == case["expected_chapter"]
        assert result["metadata"]["page_number"] == case["expected_page"]
        assert case["expected_answer_evidence"] in result["text"]
        assert result["score"] >= 0.10

    monkeypatch.setattr("backend.RAG.new_rag_query.MIN_SIMILARITY_THRESHOLD", 0.75)
    negative = engine.answer_question(
        "What does the Balbharati source say about a quasar?",
        top_k=5,
        source="Balbharati",
    )
    assert negative["retrieved"] == []
    assert negative["answer"] == "No relevant context found."

    monkeypatch.setattr("backend.RAG.new_rag_query.MIN_SIMILARITY_THRESHOLD", 0.10)
    answer = engine.answer_question(
        BALBHARATI_RETRIEVAL_CASES[1]["query"],
        top_k=5,
        class_level="1",
        subject="English",
        source="Balbharati",
    )
    assert answer["retrieved"]
    assert "103050001.pdf (page 5)" in answer["answer"]
    top_text = answer["retrieved"][0]["text"]
    assert top_text[:80] in answer["answer"]

    with sqlite3.connect(version_dir / "balbharati_chunks.db") as connection:
        columns_after = [row[1] for row in connection.execute("PRAGMA table_info(chunks)")]
    assert columns_after == columns_before


def test_metadata_is_taken_from_pdf_text_not_directory_names(tmp_path):
    from backend.scripts.build_balbharati_staging import extract_verified_metadata

    misleading_path = tmp_path / "class_5" / "history" / "book.pdf"
    misleading_path.parent.mkdir(parents=True)
    misleading_path.write_bytes(b"source metadata test")
    metadata = extract_verified_metadata(
        misleading_path,
        "ENGLISH BALBHARATI GRADE ONE",
    )

    assert metadata["standard"] == 1
    assert metadata["subject"] == "English"
    assert metadata["medium"] == "English"
    expected_path = misleading_path.resolve().relative_to(Path(__file__).resolve().parents[2]).as_posix()
    assert metadata["source_path"] == expected_path