import json
import sqlite3
import sys
from pathlib import Path
import types

import pytest

from retrieval import retriever as dense_retriever
from retrieval import unified_rag_engine as unified


def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"artifact")
    return path


def test_path_resolution_prefers_all_artifacts_from_active_pointer(tmp_path, monkeypatch):
    rag_root = tmp_path / "RAG"
    version = rag_root / "indices" / "active"
    _touch(rag_root / "chunks.db")
    _touch(rag_root / "faiss_index.bin")
    for name in ("chunks.db", "faiss_index.bin", "index_metadata.json"):
        _touch(version / name)
    (rag_root / "active_index.json").write_text(json.dumps({
        "database_path": "indices/active/chunks.db",
        "index_path": "indices/active/faiss_index.bin",
        "metadata_path": "indices/active/index_metadata.json",
    }), encoding="utf-8")
    monkeypatch.setattr(unified, "RAG_DIR", rag_root)
    monkeypatch.setattr(unified, "ROOT_DIR", tmp_path)
    for name in ("UNIGURU_RAG_DB_PATH", "UNIGURU_RAG_INDEX_PATH", "UNIGURU_RAG_METADATA_PATH"):
        monkeypatch.delenv(name, raising=False)

    db, index, metadata = unified._resolve_rag_paths()

    assert db == version / "chunks.db"
    assert index == version / "faiss_index.bin"
    assert metadata == version / "index_metadata.json"


def test_engine_loads_embedder_named_by_selected_metadata(tmp_path, monkeypatch):
    db_path = _touch(tmp_path / "chunks.db")
    index_path = _touch(tmp_path / "faiss.bin")
    metadata_path = tmp_path / "index_metadata.json"
    metadata_path.write_text(json.dumps({"embedding_model": "test-embedding", "embedding_dimension": 3}), encoding="utf-8")
    model_names = []

    class Model:
        def __init__(self, name):
            model_names.append(name)

        @staticmethod
        def get_embedding_dimension():
            return 3

    class Index:
        d = 3

    fake_faiss = types.ModuleType("faiss")
    fake_faiss.read_index = lambda _path: Index()
    fake_transformers = types.ModuleType("sentence_transformers")
    fake_transformers.SentenceTransformer = Model
    monkeypatch.setitem(sys.modules, "faiss", fake_faiss)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_transformers)
    monkeypatch.setattr(unified, "DB_PATH", db_path)
    monkeypatch.setattr(unified, "FAISS_PATH", index_path)
    monkeypatch.setattr(unified, "METADATA_PATH", metadata_path)
    monkeypatch.setattr(unified, "LOGS_DIR", tmp_path / "logs")

    engine = unified.UnifiedRAGEngine()

    assert model_names == ["test-embedding"]
    assert engine.model_name == "test-embedding"


def test_engine_rejects_embedder_index_dimension_mismatch(tmp_path, monkeypatch):
    db_path = _touch(tmp_path / "chunks.db")
    index_path = _touch(tmp_path / "faiss.bin")
    metadata_path = tmp_path / "index_metadata.json"
    metadata_path.write_text(json.dumps({"embedding_model": "test-embedding", "embedding_dimension": 3}), encoding="utf-8")

    class Model:
        def __init__(self, _name):
            pass

        @staticmethod
        def get_embedding_dimension():
            return 4

    class Index:
        d = 4

    fake_faiss = types.ModuleType("faiss")
    fake_faiss.read_index = lambda _path: Index()
    fake_transformers = types.ModuleType("sentence_transformers")
    fake_transformers.SentenceTransformer = Model
    monkeypatch.setitem(sys.modules, "faiss", fake_faiss)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_transformers)
    monkeypatch.setattr(unified, "DB_PATH", db_path)
    monkeypatch.setattr(unified, "FAISS_PATH", index_path)
    monkeypatch.setattr(unified, "METADATA_PATH", metadata_path)
    monkeypatch.setattr(unified, "LOGS_DIR", tmp_path / "logs")

    with pytest.raises(ValueError, match="metadata dimension"):
        unified.UnifiedRAGEngine()


def test_explicit_metadata_scope_excludes_nonmatching_hybrid_candidates(tmp_path, monkeypatch):
    db_path = tmp_path / "chunks.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("""CREATE TABLE chunks (
            id INTEGER PRIMARY KEY, grade TEXT, subject TEXT, domain TEXT,
            text TEXT, file_name TEXT, topic TEXT, chapter TEXT
        )""")
        connection.executemany("INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [
            (1, "Grade 8", "Mathematics", "curriculum", "matched evidence", "a.md", "math", "algebra"),
            (2, "Grade 9", "Mathematics", "curriculum", "wrong grade", "b.md", "math", "algebra"),
            (3, "Grade 8", "Science", "curriculum", "wrong subject", "c.md", "science", "biology"),
            (4, "Grade 8", "Mathematics", "history", "wrong domain", "d.md", "math", "algebra"),
        ])

    engine = unified.UnifiedRAGEngine.__new__(unified.UnifiedRAGEngine)
    engine.db_path = str(db_path)
    engine.canonicalize_query = lambda _query: ("query", {
        "grade": 8, "subject": "Mathematics", "domain": "curriculum",
    })
    engine._dense_search = lambda _query, top_k=35: [(i, 0.9) for i in (1, 2, 3, 4)]
    engine._bm25_fts_search = lambda _query, top_k=35: [(i, 0.8) for i in (1, 2, 3, 4)]
    monkeypatch.setattr(unified, "MIN_COSINE_SIMILARITY", 0.38)

    result = engine.retrieve("Class 8 mathematics", top_k=5)

    assert [row["id"] for row in result["candidates"]] == [1]
    assert [row["id"] for row in result["top_evidence"]] == [1]


def _install_dense_loader_mocks(monkeypatch, db_path, index_path):
    class Index:
        ntotal = 1
        d = 3
        id_map = object()

    fake_faiss = types.ModuleType("faiss")
    fake_faiss.read_index = lambda _path: Index()
    fake_faiss.vector_to_array = lambda _id_map: [1]
    fake_transformers = types.ModuleType("sentence_transformers")

    class Model:
        def __init__(self, _name):
            pass

        @staticmethod
        def get_embedding_dimension():
            return 3

    fake_transformers.SentenceTransformer = Model
    monkeypatch.setitem(sys.modules, "faiss", fake_faiss)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_transformers)
    monkeypatch.setattr(dense_retriever, "_active_index_paths", lambda: (db_path, index_path, db_path.parent / "index_metadata.json"))
    monkeypatch.setattr(dense_retriever, "_DENSE_STATE", None)
    monkeypatch.setattr(dense_retriever, "_DENSE_STATE_KEY", None)
    monkeypatch.setattr(dense_retriever, "_DENSE_UNAVAILABLE_KEY", None)


def test_legacy_dense_index_without_manifest_loads_when_artifacts_are_consistent(tmp_path, monkeypatch):
    db_path = tmp_path / "chunks.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE chunks (id INTEGER PRIMARY KEY)")
        connection.execute("INSERT INTO chunks VALUES (1)")
    index_path = _touch(tmp_path / "faiss.bin")
    (tmp_path / "index_metadata.json").write_text(json.dumps({"embedding_model": "test-embedding"}), encoding="utf-8")
    _install_dense_loader_mocks(monkeypatch, db_path, index_path)

    assert dense_retriever._load_dense_state() is not None


def test_manifest_backed_dense_index_still_rejects_stale_sources(tmp_path, monkeypatch):
    db_path = tmp_path / "chunks.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE chunks (id INTEGER PRIMARY KEY)")
        connection.execute("INSERT INTO chunks VALUES (1)")
    index_path = _touch(tmp_path / "faiss.bin")
    (tmp_path / "index_metadata.json").write_text(json.dumps({
        "embedding_model": "test-embedding", "source_manifest_sha256": "stale-manifest",
    }), encoding="utf-8")
    _install_dense_loader_mocks(monkeypatch, db_path, index_path)

    assert dense_retriever._load_dense_state() is None


def test_eval_cases_use_real_corpus_anchors_and_cover_requested_query_types():
    cases_path = Path(__file__).parent / "data" / "retrieval_eval_cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    knowledge_root = Path(dense_retriever._KB_ROOT)

    assert len(cases) >= 30
    assert {case["category"] for case in cases} >= {
        "factual", "multi_document", "misspelled",
        "underspecified_unanswerable", "unrelated",
    }
    assert all(
        (knowledge_root / source).is_file()
        for case in cases for source in case["expected_sources"]
    )


def test_source_manifest_cache_reuses_unchanged_corpus_and_invalidates_edits(tmp_path, monkeypatch):
    corpus = tmp_path / "knowledge"
    corpus.mkdir()
    source = corpus / "topic.md"
    source.write_text("original source text", encoding="utf-8")
    monkeypatch.setattr(dense_retriever, "_KB_ROOT", str(corpus))
    dense_retriever._SOURCE_MANIFEST_CACHE.pop(str(corpus.resolve()), None)
    original_read_text = Path.read_text
    reads = []

    def counted_read_text(path, *args, **kwargs):
        if path == source:
            reads.append(path)
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", counted_read_text)
    first = dense_retriever._current_source_manifest_hash()
    assert dense_retriever._current_source_manifest_hash() == first
    assert len(reads) == 1

    source.write_text("edited source with changed corpus bytes", encoding="utf-8")
    second = dense_retriever._current_source_manifest_hash()
    assert second != first
    assert len(reads) == 2


def test_unavailable_dense_loader_is_cached_until_index_artifacts_change(tmp_path, monkeypatch):
    db_path = tmp_path / "chunks.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE chunks (id INTEGER PRIMARY KEY)")
        connection.execute("INSERT INTO chunks VALUES (1)")
    index_path = _touch(tmp_path / "faiss.bin")
    (tmp_path / "index_metadata.json").write_text("{}", encoding="utf-8")
    _install_dense_loader_mocks(monkeypatch, db_path, index_path)
    monkeypatch.setitem(sys.modules, "faiss", None)
    original_manifest = dense_retriever._current_source_manifest_hash
    manifest_calls = []

    def counted_manifest():
        manifest_calls.append(True)
        return original_manifest()

    monkeypatch.setattr(dense_retriever, "_current_source_manifest_hash", counted_manifest)

    assert dense_retriever._load_dense_state() is None
    assert dense_retriever._load_dense_state() is None
    assert len(manifest_calls) == 1

    index_path.write_bytes(b"changed-index-artifact")
    assert dense_retriever._load_dense_state() is None
    assert len(manifest_calls) == 2
