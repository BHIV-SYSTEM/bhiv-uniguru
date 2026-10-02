"""Build a validated, isolated Balbharati RAG index without touching live indexes."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
SOURCE_DIR = BACKEND / "knowledge" / "balbharti"
STAGING_DIR = BACKEND / "RAG" / "balbharati_staging"
OCR_CACHE_DIR = STAGING_DIR / "page_cache"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
MIN_NATIVE_TEXT_CHARS = 50
CHUNK_SIZE_WORDS = 400
CHUNK_OVERLAP_WORDS = 50
EXTRACTOR_VERSION = "balbharati_page_cache_v1"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ingest_knowledge import TextChunker

logger = logging.getLogger("uniguru.balbharati.staging")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_json_atomic(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temp_path, path)


def _standard_from_text(text: str) -> Optional[int]:
    lower = str(text or "").lower()
    number_words = {
        "one": 1, "first": 1, "two": 2, "second": 2, "three": 3, "third": 3,
        "four": 4, "fourth": 4, "five": 5, "fifth": 5, "six": 6, "sixth": 6,
        "seven": 7, "seventh": 7, "eight": 8, "eighth": 8, "nine": 9,
        "ninth": 9, "ten": 10, "tenth": 10, "eleven": 11, "eleventh": 11,
        "twelve": 12, "twelfth": 12,
    }
    match = re.search(r"\b(?:grade|class|standard)\s+(one|first|two|second|three|third|four|fourth|five|fifth|six|sixth|seven|seventh|eight|eighth|nine|ninth|ten|tenth|eleven|eleventh|twelve|twelfth|\d{1,2})\b", lower)
    if match:
        value = match.group(1)
        return int(value) if value.isdigit() else number_words.get(value)

    devanagari = {
        "पहली": 1, "पहिला": 1, "पहिली": 1, "दूसरी": 2, "दुसरी": 2,
        "तीसरी": 3, "तिसरी": 3, "चौथी": 4, "चौथा": 4, "पांचवीं": 5,
        "पांचवी": 5, "पाचवी": 5, "छठी": 6, "सहावी": 6, "सातवीं": 7,
        "सातवी": 7, "आठवीं": 8, "आठवी": 8, "नौवीं": 9, "नववी": 9,
        "दसवीं": 10, "दहावी": 10, "ग्यारहवीं": 11, "अकरावी": 11,
        "बारहवीं": 12, "बारावी": 12,
    }
    match = re.search(r"(?:इयत्ता[\u0900-\u097F]*\s*|कक्षा\s*)([\u0900-\u097F]+|[0-9०-९]{1,2})", text)
    if not match:
        match = re.search(r"(पहली|दूसरी|तीसरी|चौथी|पांचवीं|छठी|सातवीं|आठवीं|नौवीं|दसवीं)\s*कक्षा", text)
    if not match:
        return None
    value = match.group(1)
    if value.isdigit():
        return int(value)
    digit_map = str.maketrans("०१२३४५६७८९", "0123456789")
    if value.translate(digit_map).isdigit():
        return int(value.translate(digit_map))
    return devanagari.get(value)


def _subject_from_text(text: str) -> Optional[str]:
    lower = " ".join(str(text or "").lower().split())
    if "परिसर अभ्यास" in text:
        return "EVS"
    if "english balbharati" in lower or "english textbook" in lower:
        return "English"
    if "मराठी बालभारती" in text:
        return "Marathi"
    if "हिंदी बालभारती" in text:
        return "Hindi"
    if "gujarati balbharati" in lower or "ગુજરાતી બાલભારતી" in text:
        return "Gujarati"
    for subject in ("mathematics", "science", "history", "geography", "civics"):
        if re.search(rf"\b{subject}\b", lower):
            return subject.title()
    return None


def _medium_from_text(text: str, subject: Optional[str]) -> Optional[str]:
    lower = " ".join(str(text or "").lower().split())
    if "english balbharati" in lower or "english textbook" in lower:
        return "English"
    if "मराठी बालभारती" in text or "इयत्ता" in text and re.search(r"[\u0900-\u097F]", text):
        if "हिंदी बालभारती" not in text and subject != "Hindi":
            return "Marathi"
    if "हिंदी बालभारती" in text or "पहली कक्षा" in text:
        return "Hindi"
    if "gujarati balbharati" in lower or "ગુજરાતી બાલભારતી" in text:
        return "Gujarati"
    return None


def extract_verified_metadata(
    pdf_path: Path,
    cover_text: str,
    pdf_title: str = "",
) -> Dict[str, Any]:
    evidence = "\n".join(part for part in (pdf_title, cover_text) if part)
    standard = _standard_from_text(evidence)
    subject = _subject_from_text(evidence)
    medium = _medium_from_text(evidence, subject)
    try:
        relative_path = pdf_path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        relative_path = pdf_path.resolve().as_posix()
    return {
        "source": "Balbharati",
        "document_id": _sha256(pdf_path),
        "filename": pdf_path.name,
        "source_path": relative_path,
        "standard": standard,
        "subject": subject,
        "medium": medium,
        "chapter": None,
        "metadata_status": "VERIFIED_FROM_DOCUMENT" if standard and subject else "PARTIAL_FROM_DOCUMENT",
        "metadata_evidence": evidence[:2000],
    }


class CachedPDFExtractor:
    def __init__(self, cache_dir: Path, enable_easyocr: bool = False, retry_failed: bool = False) -> None:
        self.cache_dir = Path(cache_dir)
        self.enable_easyocr = enable_easyocr
        self.retry_failed = retry_failed
        self._fitz = None
        self._easy_reader = None
        self.page_errors: List[Dict[str, Any]] = []
        self.cache_hits = 0
        self.cache_misses = 0

    def _get_fitz(self):
        if self._fitz is None:
            import fitz
            self._fitz = fitz
        return self._fitz

    def _ocr(self, page) -> Tuple[str, str]:
        try:
            import pytesseract
            from PIL import Image
            import io

            pix = page.get_pixmap(dpi=120, alpha=False)
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(image, lang="mar+hin+eng")
            return " ".join(text.split()), "tesseract"
        except Exception as tesseract_error:
            if not self.enable_easyocr:
                return "", f"unavailable: {type(tesseract_error).__name__}"
        try:
            import easyocr
            import numpy as np

            if self._easy_reader is None:
                self._easy_reader = easyocr.Reader(
                    ["en", "mr", "hi"], gpu=False, download_enabled=False, verbose=False
                )
            pix = page.get_pixmap(dpi=110, alpha=False)
            image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            text = "\n".join(self._easy_reader.readtext(image, detail=0, paragraph=True))
            return " ".join(text.split()), "easyocr"
        except Exception as easyocr_error:
            return "", f"unavailable: {type(easyocr_error).__name__}: {easyocr_error}"

    def extract(self, pdf_path: Path, document_id: str) -> Dict[str, Any]:
        fitz = self._get_fitz()
        doc = fitz.open(str(pdf_path))
        pdf_title = str(doc.metadata.get("title") or "")
        pages: List[Dict[str, Any]] = []
        page_cache = self.cache_dir / document_id
        try:
            for page_index in range(len(doc)):
                page_number = page_index + 1
                cache_path = page_cache / f"page-{page_number:05d}.json"
                cached = None
                if cache_path.exists():
                    try:
                        cached = json.loads(cache_path.read_text(encoding="utf-8"))
                    except Exception:
                        cached = None
                if cached and cached.get("extractor_version") == EXTRACTOR_VERSION:
                    if not (self.retry_failed and cached.get("ocr_status") == "failed"):
                        self.cache_hits += 1
                        pages.append(cached)
                        continue
                self.cache_misses += 1

                page = doc[page_index]
                native = "\n".join(page.get_text("text").splitlines()).strip()
                needs_ocr = len(" ".join(native.split())) < MIN_NATIVE_TEXT_CHARS
                text = " ".join(native.split())
                ocr_backend = None
                ocr_error = None
                is_blank = not native and not page.get_images(full=True)
                if needs_ocr and not is_blank:
                    ocr_text, ocr_backend = self._ocr(page)
                    if len(ocr_text) > len(text):
                        text = ocr_text
                    if len(text) < MIN_NATIVE_TEXT_CHARS:
                        ocr_error = str(ocr_backend)
                        self.page_errors.append(
                            {"file": pdf_path.as_posix(), "page": page_number, "reason": ocr_error}
                        )

                record = {
                    "extractor_version": EXTRACTOR_VERSION,
                    "document_id": document_id,
                    "page_number": page_number,
                    "text": text,
                    "native_char_count": len(native),
                    "char_count": len(text),
                    "ocr_required": needs_ocr and not is_blank,
                    "ocr_backend": ocr_backend,
                    "ocr_status": "failed" if ocr_error else ("success" if ocr_backend and text else "not_required"),
                    "page_status": "blank" if is_blank else ("unreadable" if ocr_error else "success"),
                    "error": ocr_error,
                }
                _write_json_atomic(cache_path, record)
                pages.append(record)
        finally:
            doc.close()
        return {"pages": pages, "pdf_title": pdf_title}


def _detect_chapter(text: str, current: Optional[str]) -> Optional[str]:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    for index, line in enumerate(lines[:8]):
        candidate = line.strip()
        if re.match(r"^chapter\s+[ivxlcdm]+(?:\s+[a-z])?$", candidate, re.IGNORECASE):
            if index + 1 < len(lines) and 1 < len(lines[index + 1]) <= 160:
                return lines[index + 1]
        if re.match(r"^(?:part|भाग)\s+[0-9०-९]+(?:\s*[a-zक-ह])?$", candidate, re.IGNORECASE):
            if index + 1 < len(lines) and 1 < len(lines[index + 1]) <= 160:
                return lines[index + 1]
        if re.match(r"^(?:chapter|lesson|unit|धडा|प्रकरण)\s*\d+|^\d+[.:-]\s*\S", candidate, re.IGNORECASE):
            return candidate[:160]
    return current


def _new_stage_database(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(
        """
        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            filename TEXT NOT NULL,
            source_path TEXT NOT NULL,
            standard INTEGER,
            subject TEXT,
            medium TEXT,
            page_count INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        );
        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY,
            chunk_id TEXT NOT NULL UNIQUE,
            document_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            source_path TEXT NOT NULL,
            page_number INTEGER NOT NULL,
            text TEXT NOT NULL,
            class_level TEXT,
            subject TEXT,
            chapter TEXT,
            source TEXT NOT NULL,
            language TEXT,
            domain TEXT NOT NULL,
            type TEXT NOT NULL,
            topic TEXT,
            metadata_json TEXT NOT NULL,
            FOREIGN KEY(document_id) REFERENCES documents(document_id)
        );
        CREATE INDEX chunks_class_subject ON chunks(class_level, subject);
        CREATE INDEX chunks_document_page ON chunks(document_id, page_number);
        """
    )
    return conn


def validate_staging_index(version_dir: Path) -> Dict[str, Any]:
    import faiss

    db_path = version_dir / "balbharati_chunks.db"
    index_path = version_dir / "balbharati_index.faiss"
    manifest_path = version_dir / "balbharati_manifest.json"
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT id, chunk_id, document_id, source_path, text FROM chunks ORDER BY id").fetchall()
        documents = conn.execute("SELECT document_id FROM documents").fetchall()
    index = faiss.read_index(str(index_path))
    vector_ids = {int(value) for value in faiss.vector_to_array(index.id_map)} if hasattr(index, "id_map") else set()
    db_ids = {int(row[0]) for row in rows}
    chunk_ids = [row[1] for row in rows]
    document_ids = {row[0] for row in documents}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = {
        "chunk_rows": len(rows),
        "vector_count": int(index.ntotal),
        "vector_dimension": int(index.d),
        "db_vector_id_match": db_ids == vector_ids,
        "orphan_vector_ids": sorted(vector_ids - db_ids),
        "orphan_db_ids": sorted(db_ids - vector_ids),
        "duplicate_chunk_ids": len(chunk_ids) - len(set(chunk_ids)),
        "missing_document_records": sum(1 for row in rows if row[2] not in document_ids),
        "missing_source_paths": sum(1 for row in rows if not row[3]),
        "empty_chunks": sum(1 for row in rows if not str(row[4] or "").strip()),
        "manifest_chunk_count": int(manifest.get("chunk_count") or 0),
        "manifest_document_count": int(manifest.get("document_count") or 0),
        "manifest_version": manifest.get("version"),
    }
    report["valid"] = bool(
        report["chunk_rows"] > 0
        and report["chunk_rows"] == report["vector_count"] == report["manifest_chunk_count"]
        and report["db_vector_id_match"]
        and report["duplicate_chunk_ids"] == 0
        and report["missing_document_records"] == 0
        and report["missing_source_paths"] == 0
        and report["empty_chunks"] == 0
        and report["manifest_document_count"] == len(document_ids)
    )
    return report


def _build_index(
    version_dir: Path,
    documents: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]],
    model_name: str = EMBEDDING_MODEL,
    model=None,
) -> Dict[str, Any]:
    import faiss

    version_dir.mkdir(parents=True, exist_ok=True)
    db_path = version_dir / "balbharati_chunks.db"
    index_path = version_dir / "balbharati_index.faiss"
    conn = _new_stage_database(db_path)
    try:
        for document in documents:
            conn.execute(
                "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    document["document_id"], document["source"], document["filename"],
                    document["source_path"], document.get("standard"), document.get("subject"),
                    document.get("medium"), document["page_count"], document["sha256"],
                    json.dumps(document, ensure_ascii=False),
                ),
            )
        texts: List[str] = []
        vector_ids: List[int] = []
        for index, chunk in enumerate(chunks, start=1):
            conn.execute(
                "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    index, chunk["chunk_id"], chunk["document_id"], chunk["file_name"],
                    chunk["source_path"], chunk["page_number"], chunk["text"],
                    str(chunk["standard"]) if chunk.get("standard") is not None else None,
                    chunk.get("subject"), chunk.get("chapter"), chunk["source"],
                    chunk.get("medium"), "education", "textbook", chunk.get("topic"),
                    json.dumps(chunk.get("metadata") or {}, ensure_ascii=False),
                ),
            )
            texts.append(chunk["text"])
            vector_ids.append(index)
        conn.commit()
    finally:
        conn.close()

    if model is None:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(model_name)
    embeddings = np.asarray(
        model.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True),
        dtype=np.float32,
    )
    if embeddings.ndim != 2 or embeddings.shape[0] != len(chunks) or embeddings.shape[1] <= 0:
        raise ValueError("Embedding output shape does not match staging chunk count.")
    base_index = faiss.IndexFlatL2(int(embeddings.shape[1]))
    index = faiss.IndexIDMap2(base_index)
    index.add_with_ids(embeddings, np.asarray(vector_ids, dtype=np.int64))
    faiss.write_index(index, str(index_path))

    manifest = {
        "schema_version": "UNIGURU_BALBHARATI_STAGING_V1",
        "version": version_dir.name,
        "status": "READY_FOR_ISOLATED_RETRIEVAL_TESTS",
        "source": "Balbharati",
        "source_root": "backend/knowledge/balbharti",
        "embedding_model": model_name,
        "embedding_dimension": int(embeddings.shape[1]),
        "vector_index_type": "IndexIDMap2(IndexFlatL2)",
        "chunk_count": len(chunks),
        "document_count": len(documents),
        "documents": documents,
    }
    _write_json_atomic(version_dir / "balbharati_manifest.json", manifest)
    integrity = validate_staging_index(version_dir)
    if not integrity["valid"]:
        raise RuntimeError(f"Staging index failed integrity checks: {integrity}")
    return integrity


def build_staging_index(
    source_dir: Path = SOURCE_DIR,
    staging_dir: Path = STAGING_DIR,
    enable_easyocr: bool = False,
    retry_failed: bool = False,
    model_name: str = EMBEDDING_MODEL,
    model=None,
    pdf_extractor: Optional[CachedPDFExtractor] = None,
    chunker: Optional[TextChunker] = None,
) -> Dict[str, Any]:
    source_dir = Path(source_dir).resolve()
    staging_dir = Path(staging_dir).resolve()
    cache_dir = staging_dir / "page_cache"
    version = datetime.now(timezone.utc).strftime("balbharati-%Y%m%dT%H%M%S.%fZ")
    pdf_paths = sorted(source_dir.rglob("*.pdf"))
    report: Dict[str, Any] = {
        "version": version,
        "status": "PREPROCESSING",
        "source_pdf_count": len(pdf_paths),
        "unique_documents": 0,
        "duplicate_files_skipped": 0,
        "pages_total": 0,
        "native_text_pages": 0,
        "page_cache_hits": 0,
        "page_cache_misses": 0,
        "ocr_pages_required": 0,
        "ocr_pages_succeeded": 0,
        "blank_pages": 0,
        "failed_pages": [],
        "failed_documents": [],
        "chunks_created": 0,
        "processed_files": [],
    }
    documents: List[Dict[str, Any]] = []
    chunks: List[Dict[str, Any]] = []
    seen_document_ids: Dict[str, Dict[str, Any]] = {}
    extractor = pdf_extractor or CachedPDFExtractor(
        cache_dir, enable_easyocr=enable_easyocr, retry_failed=retry_failed
    )
    text_chunker = chunker or TextChunker(max_words=CHUNK_SIZE_WORDS, overlap_words=CHUNK_OVERLAP_WORDS)

    for pdf_path in pdf_paths:
        try:
            document_id = _sha256(pdf_path)
            try:
                relative_path = pdf_path.resolve().relative_to(ROOT.resolve()).as_posix()
            except ValueError:
                relative_path = pdf_path.resolve().as_posix()
            if document_id in seen_document_ids:
                seen_document_ids[document_id].setdefault("duplicate_paths", []).append(relative_path)
                report["duplicate_files_skipped"] += 1
                continue

            extracted = extractor.extract(pdf_path, document_id)
            report["page_cache_hits"] = extractor.cache_hits
            report["page_cache_misses"] = extractor.cache_misses
            page_records = extracted["pages"]
            report["pages_total"] += len(page_records)
            cover_text = "\n".join(page["text"] for page in page_records[:4])
            metadata = extract_verified_metadata(pdf_path, cover_text, extracted.get("pdf_title", ""))
            document = {
                **metadata,
                "sha256": document_id,
                "page_count": len(page_records),
                "duplicate_paths": [],
            }
            documents.append(document)
            seen_document_ids[document_id] = document

            current_chapter = None
            for page_record in page_records:
                text = str(page_record.get("text") or "").strip()
                if page_record.get("native_char_count", 0) >= MIN_NATIVE_TEXT_CHARS:
                    report["native_text_pages"] += 1
                if page_record.get("ocr_required"):
                    report["ocr_pages_required"] += 1
                    if page_record.get("ocr_status") == "success":
                        report["ocr_pages_succeeded"] += 1
                if page_record.get("page_status") == "blank":
                    report["blank_pages"] += 1
                if page_record.get("page_status") == "unreadable":
                    report["failed_pages"].append(
                        {"source_path": relative_path, "page": page_record["page_number"], "error": page_record.get("error")}
                    )
                if not text:
                    continue

                current_chapter = _detect_chapter(text, current_chapter)
                for chunk_number, chunk_text in enumerate(text_chunker.chunk_text(text), start=1):
                    chunk_id = _sha_text(
                        f"{document_id}:{page_record['page_number']}:{chunk_number}:{chunk_text}"
                    )
                    chunks.append(
                        {
                            "chunk_id": chunk_id,
                            "document_id": document_id,
                            "file_name": pdf_path.name,
                            "source_path": relative_path,
                            "page_number": int(page_record["page_number"]),
                            "text": chunk_text,
                            "standard": metadata.get("standard"),
                            "subject": metadata.get("subject"),
                            "medium": metadata.get("medium"),
                            "chapter": current_chapter,
                            "source": "Balbharati",
                            "topic": None,
                            "metadata": {
                                "metadata_status": metadata["metadata_status"],
                                "extractor_version": EXTRACTOR_VERSION,
                                "native_char_count": page_record.get("native_char_count"),
                                "ocr_backend": page_record.get("ocr_backend"),
                            },
                        }
                    )
            report["processed_files"].append(relative_path)
        except Exception as exc:
            report["failed_documents"].append({"path": pdf_path.as_posix(), "error": str(exc)})
            logger.exception("Failed to preprocess Balbharati PDF %s", pdf_path)

    report["unique_documents"] = len(documents)
    report["chunks_created"] = len(chunks)
    report["metadata_unverified_documents"] = sum(
        1 for document in documents if document["metadata_status"] != "VERIFIED_FROM_DOCUMENT"
    )
    report["ready_for_index_build"] = bool(
        pdf_paths
        and not report["failed_documents"]
        and not report["failed_pages"]
        and chunks
    )

    staging_dir.mkdir(parents=True, exist_ok=True)
    if not report["ready_for_index_build"]:
        report["status"] = "INCOMPLETE_NO_INDEX_WRITTEN"
        _write_json_atomic(staging_dir / "balbharati_processing_report.json", report)
        return report

    final_dir = staging_dir / "versions" / version
    final_dir.mkdir(parents=True, exist_ok=False)
    try:
        integrity = _build_index(final_dir, documents, chunks, model_name=model_name, model=model)
        report["integrity"] = integrity
        report["status"] = "READY_FOR_ISOLATED_RETRIEVAL_TESTS"
        _write_json_atomic(final_dir / "balbharati_processing_report.json", report)
    except Exception:
        shutil.rmtree(final_dir, ignore_errors=True)
        raise

    report["version_dir"] = str(final_dir)
    _write_json_atomic(staging_dir / "balbharati_processing_report.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an isolated, validated Balbharati staging index.")
    parser.add_argument("--source-dir", type=Path, default=SOURCE_DIR)
    parser.add_argument("--staging-dir", type=Path, default=STAGING_DIR)
    parser.add_argument("--enable-easyocr", action="store_true", help="Use cached EasyOCR for pages not handled by Tesseract.")
    parser.add_argument("--retry-failed", action="store_true", help="Retry page cache entries previously marked OCR failure.")
    parser.add_argument("--model", default=EMBEDDING_MODEL)
    args = parser.parse_args()
    report = build_staging_index(
        source_dir=args.source_dir,
        staging_dir=args.staging_dir,
        enable_easyocr=args.enable_easyocr,
        retry_failed=args.retry_failed,
        model_name=args.model,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report["status"] == "INCOMPLETE_NO_INDEX_WRITTEN":
        raise SystemExit(2)


if __name__ == "__main__":
    main()