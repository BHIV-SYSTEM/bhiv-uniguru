"""Build a versioned FAISS/SQLite index from the active Markdown knowledge base."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_ROOT = BACKEND_ROOT / "knowledge"
RAG_ROOT = BACKEND_ROOT / "RAG"
DEFAULT_OUTPUT_ROOT = RAG_ROOT / "indices"
DEFAULT_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 2500
CHUNK_OVERLAP = 200


def _split_chunks(text: str) -> list[tuple[str, str]]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        if end < len(text):
            boundary = max(text.rfind("\n\n", start, end), text.rfind("\n", start, end))
            if boundary > start + (CHUNK_SIZE // 2):
                end = boundary
        content = text[start:end].strip()
        if content:
            headings = re.findall(r"^#{1,6}\s+(.+?)\s*$", text[:start], re.MULTILINE)
            if end > start:
                headings.extend(re.findall(r"^#{1,6}\s+(.+?)\s*$", text[start:end], re.MULTILINE))
            chunks.append((content, headings[-1] if headings else ""))
        if end >= len(text):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def _source_records() -> tuple[list[dict], str]:
    files = sorted(path for path in KNOWLEDGE_ROOT.rglob("*.md") if path.is_file())
    records = []
    manifest = hashlib.sha256()
    for path in files:
        text = path.read_text(encoding="utf-8")
        relative_path = path.relative_to(KNOWLEDGE_ROOT).as_posix()
        file_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        manifest.update(f"{relative_path}:{file_hash}\n".encode("utf-8"))
        for chunk_number, (content, chapter) in enumerate(_split_chunks(text)):
            records.append(
                {
                    "file_name": relative_path,
                    "page_number": None,
                    "text": content,
                    "domain": path.parent.name,
                    "category": path.parent.name,
                    "subcategory": path.parent.parent.name if path.parent.parent != KNOWLEDGE_ROOT else "",
                    "topic": path.stem,
                    "chapter": chapter,
                    "source": relative_path,
                    "language": "unknown",
                    "type": "markdown",
                    "chunk_number": chunk_number,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
    return records, manifest.hexdigest()


def _write_database(path: Path, records: list[dict], files: list[Path]) -> list[int]:
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute(
            """CREATE TABLE indexed_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT UNIQUE,
                sha256 TEXT,
                indexed_time TEXT
            )"""
        )
        connection.execute(
            """CREATE TABLE chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT,
                page_number INTEGER,
                text TEXT,
                domain TEXT,
                category TEXT,
                subcategory TEXT,
                topic TEXT,
                chapter TEXT,
                source TEXT,
                language TEXT,
                type TEXT,
                created_at TEXT,
                chunk_number INTEGER
            )"""
        )
        indexed_at = datetime.now(timezone.utc).isoformat()
        for source_path in files:
            relative_path = source_path.relative_to(KNOWLEDGE_ROOT).as_posix()
            content_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
            connection.execute(
                "INSERT INTO indexed_files (file_name, sha256, indexed_time) VALUES (?, ?, ?)",
                (relative_path, content_hash, indexed_at),
            )
        ids = []
        for record in records:
            cursor = connection.execute(
                """INSERT INTO chunks (
                    file_name, page_number, text, domain, category, subcategory,
                    topic, chapter, source, language, type, created_at, chunk_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                tuple(record[key] for key in (
                    "file_name", "page_number", "text", "domain", "category",
                    "subcategory", "topic", "chapter", "source", "language",
                    "type", "created_at", "chunk_number",
                )),
            )
            ids.append(int(cursor.lastrowid))
        connection.commit()
        connection.execute("PRAGMA integrity_check").fetchone()
        return ids
    finally:
        connection.close()


def build_index(output_root: Path, model_name: str = DEFAULT_MODEL) -> dict:
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer

    files = sorted(path for path in KNOWLEDGE_ROOT.rglob("*.md") if path.is_file())
    records, source_manifest_hash = _source_records()
    if not files or not records:
        raise RuntimeError(f"No Markdown sources found under {KNOWLEDGE_ROOT}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    index_version = f"rag-{timestamp}-{source_manifest_hash[:10]}"
    output_root.mkdir(parents=True, exist_ok=True)
    staging = output_root / f".staging-{uuid.uuid4().hex}"
    version_dir = output_root / index_version
    staging.mkdir()
    try:
        chunk_ids = _write_database(staging / "chunks.db", records, files)
        model = SentenceTransformer(model_name)
        embeddings = model.encode(
            [record["text"] for record in records],
            batch_size=64,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        embeddings = np.asarray(embeddings, dtype="float32")
        if embeddings.ndim != 2 or len(embeddings) != len(chunk_ids):
            raise RuntimeError("Embedding output does not align with indexed chunk IDs.")
        index = faiss.IndexIDMap2(faiss.IndexFlatIP(int(embeddings.shape[1])))
        index.add_with_ids(embeddings, np.asarray(chunk_ids, dtype="int64"))
        faiss.write_index(index, str(staging / "faiss_index.bin"))

        metadata = {
            "index_version": index_version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "embedding_model": model_name,
            "embedding_dimension": int(embeddings.shape[1]),
            "index_type": "IndexIDMap2(IndexFlatIP)",
            "metric": "cosine_similarity_normalized_inner_product",
            "source_root": str(KNOWLEDGE_ROOT),
            "source_documents": len(files),
            "indexed_documents": len(files),
            "total_chunks": len(records),
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
            "source_manifest_sha256": source_manifest_hash,
        }
        (staging / "index_metadata.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        if version_dir.exists():
            raise FileExistsError(f"Index version already exists: {version_dir}")
        staging.replace(version_dir)

        active_pointer = RAG_ROOT / "active_index.json"
        pointer = {
            "index_version": index_version,
            "database_path": (version_dir / "chunks.db").relative_to(RAG_ROOT).as_posix(),
            "index_path": (version_dir / "faiss_index.bin").relative_to(RAG_ROOT).as_posix(),
            "metadata_path": (version_dir / "index_metadata.json").relative_to(RAG_ROOT).as_posix(),
        }
        temporary_pointer = RAG_ROOT / f".active_index-{uuid.uuid4().hex}.tmp"
        temporary_pointer.write_text(json.dumps(pointer, indent=2), encoding="utf-8")
        os.replace(temporary_pointer, active_pointer)
        compatibility_metadata = RAG_ROOT / "index_metadata.json"
        temporary_metadata = RAG_ROOT / f".index_metadata-{uuid.uuid4().hex}.tmp"
        temporary_metadata.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temporary_metadata, compatibility_metadata)
        return {**metadata, **pointer}
    except Exception:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--model", default=os.getenv("UNIGURU_EMBEDDING_MODEL", DEFAULT_MODEL))
    args = parser.parse_args()
    result = build_index(args.output_root.resolve(), args.model)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()