import os
import json
import sqlite3
import tempfile
import pytest
import faiss
import numpy as np
from backend.RAG.new_rag_query import NewRAGEngine, MIN_SIMILARITY_THRESHOLD, TOP_K


def test_rag_retrieval_threshold_blocks_irrelevant_chunks(monkeypatch, tmp_path):
    # Create a fake database with one chunk that would be below threshold
    db_path = tmp_path / "chunks.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE chunks (id INTEGER PRIMARY KEY, file_name TEXT, page_number INTEGER, text TEXT)")
    conn.execute("INSERT INTO chunks (id, file_name, page_number, text) VALUES (?, ?, ?, ?)",
                 (1, "dummy.txt", 1, "Unrelated religious content about Jainism."))
    conn.commit()
    conn.close()

    # Use a fake engine that returns a low score for the query
    class FakeEngine(NewRAGEngine):
        def __init__(self, *args, **kwargs):
            self.db_path = str(db_path)
            self.ollama = None
            self.model = None
            self._faiss = None

        def retrieve(self, query: str, top_k: int = 5, **kwargs):
            return [{
                "id": 1,
                "text": "Unrelated religious content about Jainism.",
                "metadata": {"file_name": "dummy.txt", "page_number": 1},
                "score": MIN_SIMILARITY_THRESHOLD - 0.05,
            }]

    monkeypatch.setattr("backend.RAG.new_rag_query.NewRAGEngine", FakeEngine)

    engine = FakeEngine()
    result = engine.answer_question("Which user actions should trigger authentication?", top_k=TOP_K)

    assert result["answer"] == "No relevant context found."
    assert result["retrieved"] == []


def test_rag_retrieval_returns_top_relevant_chunks(monkeypatch, tmp_path):
    db_path = tmp_path / "chunks.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE chunks (id INTEGER PRIMARY KEY, file_name TEXT, page_number INTEGER, text TEXT)")
    conn.executemany(
        "INSERT INTO chunks (id, file_name, page_number, text) VALUES (?, ?, ?, ?)",
        [
            (1, "auth.txt", 1, "Authentication should trigger when users access protected pages."),
            (2, "jain.txt", 1, "Jain religious content unrelated to auth."),
        ],
    )
    conn.commit()
    conn.close()

    class FakeEngine(NewRAGEngine):
        def __init__(self, *args, **kwargs):
            self.db_path = str(db_path)
            self.ollama = None
            self.model = None
            self._faiss = None

        def retrieve(self, query: str, top_k: int = 5, **kwargs):
            return [
                {
                    "id": 1,
                    "text": "Authentication should trigger when users access protected pages.",
                    "metadata": {"file_name": "auth.txt", "page_number": 1},
                    "score": MIN_SIMILARITY_THRESHOLD + 0.05,
                },
                {
                    "id": 2,
                    "text": "Jain religious content unrelated to auth.",
                    "metadata": {"file_name": "jain.txt", "page_number": 1},
                    "score": MIN_SIMILARITY_THRESHOLD - 0.05,
                },
            ]

    monkeypatch.setattr("backend.RAG.new_rag_query.NewRAGEngine", FakeEngine)

    engine = FakeEngine()
    result = engine.answer_question("Which user actions should trigger authentication?", top_k=TOP_K)

    assert "Authentication should trigger when users access protected pages." in result["answer"]
    assert len(result["retrieved"]) == 1
    assert result["retrieved"][0]["metadata"]["file_name"] == "auth.txt"


def test_rag_retrieval_deduplicates_duplicates(monkeypatch, tmp_path):
    db_path = tmp_path / "chunks.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE chunks (id INTEGER PRIMARY KEY, file_name TEXT, page_number INTEGER, text TEXT)")
    conn.executemany(
        "INSERT INTO chunks (id, file_name, page_number, text) VALUES (?, ?, ?, ?)",
        [
            (1, "auth1.txt", 1, "Authentication should trigger when users access protected pages."),
            (2, "auth2.txt", 1, "Authentication should trigger when users access protected pages."),
        ],
    )
    conn.commit()
    conn.close()

    class FakeEngine(NewRAGEngine):
        def __init__(self, *args, **kwargs):
            self.db_path = str(db_path)
            self.ollama = None
            self.model = None
            self._faiss = None

        def retrieve(self, query: str, top_k: int = 5, **kwargs):
            return [
                {
                    "id": 1,
                    "text": "Authentication should trigger when users access protected pages.",
                    "metadata": {"file_name": "auth1.txt", "page_number": 1},
                    "score": MIN_SIMILARITY_THRESHOLD + 0.1,
                },
                {
                    "id": 2,
                    "text": "Authentication should trigger when users access protected pages.",
                    "metadata": {"file_name": "auth2.txt", "page_number": 1},
                    "score": MIN_SIMILARITY_THRESHOLD + 0.08,
                },
            ]

    monkeypatch.setattr("backend.RAG.new_rag_query.NewRAGEngine", FakeEngine)

    engine = FakeEngine()
    result = engine.answer_question("Which user actions should trigger authentication?", top_k=TOP_K)

    assert len(result["retrieved"]) == 1
    assert result["retrieved"][0]["metadata"]["file_name"] == "auth1.txt"


def test_index_flat_l2_scores_convert_squared_distance_to_cosine(tmp_path):
    db_path = tmp_path / "chunks.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """CREATE TABLE chunks (
                id INTEGER PRIMARY KEY,
                file_name TEXT,
                page_number INTEGER,
                text TEXT,
                class_level TEXT,
                subject TEXT,
                chapter TEXT,
                source TEXT,
                language TEXT,
                domain TEXT,
                type TEXT,
                topic TEXT
            )"""
        )
        conn.executemany(
            "INSERT INTO chunks (id, file_name, page_number, text, source) VALUES (?, ?, ?, ?, ?)",
            [
                (1, "matching.pdf", 1, "Matching textbook evidence.", "Balbharati"),
                (2, "orthogonal.pdf", 1, "Orthogonal textbook evidence.", "Balbharati"),
            ],
        )

    index = faiss.IndexIDMap2(faiss.IndexFlatL2(2))
    index.add_with_ids(
        np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
        np.asarray([1, 2], dtype=np.int64),
    )
    faiss_path = tmp_path / "index.faiss"
    faiss.write_index(index, str(faiss_path))

    class FixedQueryModel:
        def encode(self, texts):
            return np.asarray([[1.0, 0.0] for _ in texts], dtype=np.float32)

    engine = NewRAGEngine(db_path=db_path, faiss_path=faiss_path, model=FixedQueryModel())
    results = engine.retrieve("matching", top_k=5, source="Balbharati")

    assert len(results) == 1
    assert results[0]["metadata"]["file_name"] == "matching.pdf"
    assert results[0]["score"] == pytest.approx(1.0)
