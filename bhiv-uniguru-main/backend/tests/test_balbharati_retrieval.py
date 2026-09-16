"""Unit and integration tests for Balbharati Standards 1-12 Hybrid Retrieval System."""

import pytest
from fastapi.testclient import TestClient

from backend.retrieval.balbharati.metadata_extractor import (
    extract_balbharati_metadata,
    BalbharatiQueryMetadata,
)
from backend.retrieval.balbharati.bm25_retriever import BM25Retriever, tokenize
from backend.retrieval.balbharati.hybrid_retriever import get_balbharati_retriever, BalbharatiHybridRetriever
from backend.retrieval.balbharati.answer_synthesizer import (
    synthesize_balbharati_answer,
    format_attribution_citation,
)
from backend.service.api import app


# ── 1. Query Metadata Extraction Tests ─────────────────────────────────────────

def test_metadata_extraction_english():
    meta = extract_balbharati_metadata("Explain photosynthesis from Class 7 Science textbook")
    assert meta.standard == 7
    assert meta.subject == "Science"
    assert meta.board == "Maharashtra"
    assert meta.mode == "explain"
    assert "photosynthesis" in meta.clean_query.lower()


def test_metadata_extraction_marathi_ordinals():
    meta = extract_balbharati_metadata("इयत्ता पाचवी परिसर अभ्यास धडा २ स्वाध्याय")
    assert meta.standard == 5
    assert meta.subject == "Science"  # परिसर अभ्यास maps to Science/EVS
    assert meta.medium == "Marathi"
    assert meta.mode == "qa"
    assert meta.detected_language == "mr"


def test_metadata_extraction_roman_and_word():
    meta1 = extract_balbharati_metadata("Class VII Mathematics equations")
    assert meta1.standard == 7
    assert meta1.subject == "Mathematics"

    meta2 = extract_balbharati_metadata("Grade 10 History and Civics summary")
    assert meta2.standard == 10
    assert meta2.subject == "History"
    assert meta2.mode == "summary"


def test_metadata_cross_lingual_expansion():
    meta = extract_balbharati_metadata("इयत्ता ७ विज्ञानातील प्रकाशसंश्लेषण म्हणजे काय?")
    assert meta.standard == 7
    assert meta.subject == "Science"
    # Verify cross-lingual expansion added English academic concept
    assert "photosynthesis" in meta.clean_query.lower()
    assert meta.mode == "definition"


# ── 2. Okapi BM25 Retriever Tests ──────────────────────────────────────────────

def test_bm25_tokenization_and_stemming():
    tokens = tokenize("Living things adapt to their environments in nature")
    assert "liv" in tokens or "living" in tokens or "thing" in tokens
    assert "adapt" in tokens
    assert "environment" in tokens or "environments" in tokens


def test_bm25_indexing_and_metadata_filtering():
    retriever = BM25Retriever()
    docs = [
        {
            "chunk_id": "c1",
            "text": "Photosynthesis is the process by which green plants make food.",
            "standard": 7,
            "subject": "Science",
            "medium": "English",
            "chapter": "Plants",
        },
        {
            "chunk_id": "c2",
            "text": "The Mughal Empire was founded by Babur in 1526.",
            "standard": 7,
            "subject": "History",
            "medium": "English",
            "chapter": "Medieval India",
        },
        {
            "chunk_id": "c3",
            "text": "Photosynthesis occurs in chloroplasts containing chlorophyll.",
            "standard": 8,
            "subject": "Science",
            "medium": "English",
            "chapter": "Cell Structure",
        },
    ]
    retriever.index_documents(docs)

    # Filter by standard=7 and subject=Science
    results = retriever.search("photosynthesis plants", standard=7, subject="Science", top_k=5)
    assert len(results) >= 1
    assert results[0]["document"]["chunk_id"] == "c1"
    assert results[0]["document"]["standard"] == 7

    # Ensure History doc was excluded
    for r in results:
        assert r["document"]["subject"] == "Science"


# ── 3. Hybrid Retrieval End-to-End Tests ────────────────────────────────────────

def test_hybrid_retrieval_with_persisted_index():
    retriever = get_balbharati_retriever()
    query = "photosynthesis in green plants Class 7 Science"
    res = retriever.search_hybrid(query, top_k=3)

    assert res is not None
    assert "results" in res
    assert len(res["results"]) > 0
    assert res["confidence"] > 0.5

    top_chunk = res["results"][0]
    assert top_chunk["standard"] == 7
    assert top_chunk["subject"] == "Science"
    assert top_chunk["source"] == "Balbharati"
    assert top_chunk["page"] is not None
    assert top_chunk["chunk_id"] is not None


def test_hybrid_retrieval_deduplication():
    retriever = get_balbharati_retriever()
    res = retriever.search_hybrid("Newton laws of motion force energy Class 8 Science", top_k=5)

    assert "results" in res
    seen_texts = set()
    for item in res["results"]:
        norm = item["text"].strip().lower()
        assert norm not in seen_texts, "Duplicate text found in top results"
        seen_texts.add(norm)


# ── 4. Answer Synthesis & Evidence Attribution Tests ──────────────────────────

def test_attribution_citation_formatting():
    chunk = {
        "book": "General Science Standard 7",
        "standard": 7,
        "subject": "Science",
        "medium": "English",
        "chapter": "Living World: Adaptation and Classification",
        "page": 42,
        "source": "Balbharati",
    }
    citation = format_attribution_citation(chunk)
    assert "Source: Balbharati" in citation
    assert "Standard: 7" in citation
    assert "Subject: Science" in citation
    assert "Page: 42" in citation


def test_synthesize_balbharati_answer_with_evidence():
    retrieval_output = {
        "query": "What is photosynthesis?",
        "detected_metadata": {"standard": 7, "subject": "Science", "mode": "definition"},
        "confidence": 0.85,
        "results": [
            {
                "rank": 1,
                "score": 0.95,
                "source": "Balbharati",
                "book": "General Science Std 7",
                "standard": 7,
                "subject": "Science",
                "medium": "English",
                "chapter": "Nutrition in Living Organisms",
                "page": 26,
                "text": "Plants produce their own food with the help of sunlight and chlorophyll using water and carbon dioxide. This process is called photosynthesis.",
            }
        ],
    }
    synthesis = synthesize_balbharati_answer(retrieval_output)
    assert synthesis["available"] is True
    assert "photosynthesis" in synthesis["answer"].lower()
    assert len(synthesis["citations"]) == 1
    assert "Source: Balbharati | Standard: 7" in synthesis["citations"][0]


def test_synthesize_balbharati_answer_refusal_on_empty():
    empty_output = {
        "query": "Quantum foam in cosmology",
        "detected_metadata": {},
        "confidence": 0.0,
        "results": [],
    }
    synthesis = synthesize_balbharati_answer(empty_output)
    assert "sufficient evidence" in synthesis["answer"].lower()
    assert len(synthesis["citations"]) == 0


# ── 5. API Debug Endpoint Test ────────────────────────────────────────────────

def test_api_retrieval_debug_endpoint():
    client = TestClient(app)
    response = client.post(
        "/api/retrieval/debug",
        json={"query": "Explain digestive system in human body Class 7 Science", "top_k": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert "detected_metadata" in data
    assert "retrieval_results" in data
    assert "synthesized_answer" in data
    assert data["detected_metadata"]["standard"] == 7
    assert data["detected_metadata"]["subject"] == "Science"
