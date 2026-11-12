import sqlite3

from retrieval.unified_rag_engine import UnifiedRAGEngine


def _chunks_database(path):
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE chunks (
                id INTEGER,
                file_name TEXT,
                text TEXT,
                domain TEXT,
                category TEXT,
                topic TEXT,
                chapter TEXT,
                source TEXT,
                language TEXT,
                chunk_number INTEGER,
                content_hash TEXT,
                authority_score REAL,
                concept TEXT,
                book TEXT,
                board TEXT,
                subject TEXT,
                grade TEXT,
                section TEXT,
                page INTEGER,
                source_name TEXT,
                source_url TEXT
            )
            """
        )
        for chunk_id in (1, 2):
            connection.execute(
                """
                INSERT INTO chunks VALUES (
                    ?, ?, ?, 'knowledge', 'test', 'topic', 'chapter', 'source',
                    'English', 1, ?, 0.5, '', ?, '', '', '', '', NULL, '', ''
                )
                """,
                (chunk_id, f"source-{chunk_id}.md", f"Topic content for source {chunk_id}.",
                 f"hash-{chunk_id}", f"Book {chunk_id}"),
            )


def test_unified_rag_rrf_contributes_to_final_ranking(tmp_path):
    database = tmp_path / "chunks.db"
    _chunks_database(database)
    engine = object.__new__(UnifiedRAGEngine)
    engine.db_path = str(database)
    engine._dense_search = lambda _query, top_k: [(2, 0.5), (1, 0.9)]
    engine._bm25_fts_search = lambda _query, top_k: [(1, 100.0), (2, 0.1)]

    result = engine.retrieve("topic")

    assert result["candidates"][0]["id"] == 2
    assert result["candidates"][0]["rrf_normalized_score"] == 1.0
    assert result["candidates"][0]["rrf_score"] > result["candidates"][1]["rrf_score"]


def test_citation_omits_unavailable_page_and_section_metadata():
    citation = UnifiedRAGEngine._format_citation(
        {"file_name": "dharma.md", "source_name": "Knowledge Base"}
    )

    assert citation == ("dharma.md", "dharma.md (Source: Knowledge Base)")
    assert UnifiedRAGEngine._format_citation({"text": "No provenance"}) is None


def test_extractive_fallback_selects_only_query_relevant_sentences():
    engine = object.__new__(UnifiedRAGEngine)
    evidence = [{
        "book": "Dharma Notes",
        "file_name": "dharma.md",
        "source_name": "Knowledge Base",
        "text": "Dharma is a principle of duty and moral order. This unrelated sentence discusses astronomy.",
        "concept": "Dharma",
        "composite_score": 0.75,
    }]
    engine.retrieve = lambda _query, top_k: {
        "top_evidence": evidence,
        "is_grounded": True,
        "max_similarity": 0.7,
    }
    engine.groq_client = None
    engine._log_retrieval = lambda *args, **kwargs: None

    result = engine.answer_query("What is Dharma?")

    assert result["verification_status"] == "VERIFIED"
    assert "Dharma is a principle of duty and moral order." in result["answer"]
    assert "astronomy" not in result["answer"]
    assert "Page 1" not in result["answer"]
    assert "Authoritative Publication" not in result["answer"]
