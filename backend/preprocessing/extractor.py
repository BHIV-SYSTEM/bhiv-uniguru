"""
Document Extractor for UniGuru Preprocessing Pipeline.
Supports PDF (digitized & scanned detection), DOCX, TXT, Markdown, and YouTube/Web JSON.
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("uniguru.preprocessing.extractor")


@dataclass
class ExtractedPage:
    page_number: int
    raw_text: str
    char_count: int


@dataclass
class ExtractedDocument:
    document_id: str
    file_name: str
    file_path: str
    file_type: str
    file_size_bytes: int
    title: str
    pages: List[ExtractedPage] = field(default_factory=list)
    raw_text: str = ""
    is_scanned: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DocumentExtractor:
    """Extracts raw text and structural metadata from multiple file formats."""

    @classmethod
    def extract(cls, file_path: str | Path) -> ExtractedDocument:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {path.resolve()}")

        suffix = path.suffix.lower()
        stat = path.stat()
        file_size = stat.st_size

        # Deterministic document ID based on path and file size
        doc_id = f"doc_{uuid.uuid5(uuid.NAMESPACE_URL, str(path.resolve())).hex[:12]}"

        if suffix == ".pdf":
            return cls._extract_pdf(path, doc_id, file_size)
        elif suffix in (".txt", ".text"):
            return cls._extract_txt(path, doc_id, file_size)
        elif suffix == ".md":
            return cls._extract_markdown(path, doc_id, file_size)
        elif suffix == ".docx":
            return cls._extract_docx(path, doc_id, file_size)
        elif suffix in (".json", ".jsonl"):
            return cls._extract_json_or_transcript(path, doc_id, file_size)
        else:
            raise ValueError(f"Unsupported document format '{suffix}' for {path.name}")

    @classmethod
    def _extract_pdf(cls, path: Path, doc_id: str, file_size: int) -> ExtractedDocument:
        import fitz  # PyMuPDF

        doc = fitz.open(str(path))
        pages: List[ExtractedPage] = []
        full_text_parts: List[str] = []
        total_text_chars = 0

        for page_idx, page in enumerate(doc, start=1):
            text = page.get_text() or ""
            char_count = len(text.strip())
            total_text_chars += char_count
            pages.append(ExtractedPage(page_number=page_idx, raw_text=text, char_count=char_count))
            full_text_parts.append(text)

        avg_chars_per_page = total_text_chars / max(1, len(doc))
        is_scanned = avg_chars_per_page < 30 and len(doc) > 0

        pdf_meta = doc.metadata or {}
        title = pdf_meta.get("title") or path.stem.replace("_", " ").title()

        return ExtractedDocument(
            document_id=doc_id,
            file_name=path.name,
            file_path=str(path.resolve()),
            file_type="pdf",
            file_size_bytes=file_size,
            title=title,
            pages=pages,
            raw_text="\n\n".join(full_text_parts),
            is_scanned=is_scanned,
            metadata={
                "author": pdf_meta.get("author", "Unknown"),
                "producer": pdf_meta.get("producer", "Unknown"),
                "total_pages": len(doc),
                "avg_chars_per_page": round(avg_chars_per_page, 2),
            },
        )

    @classmethod
    def _extract_txt(cls, path: Path, doc_id: str, file_size: int) -> ExtractedDocument:
        raw = path.read_text(encoding="utf-8", errors="replace")
        return ExtractedDocument(
            document_id=doc_id,
            file_name=path.name,
            file_path=str(path.resolve()),
            file_type="txt",
            file_size_bytes=file_size,
            title=path.stem.replace("_", " ").title(),
            pages=[ExtractedPage(page_number=1, raw_text=raw, char_count=len(raw))],
            raw_text=raw,
            is_scanned=False,
            metadata={},
        )

    @classmethod
    def _extract_markdown(cls, path: Path, doc_id: str, file_size: int) -> ExtractedDocument:
        raw = path.read_text(encoding="utf-8", errors="replace")
        meta = {}
        content = raw

        # Parse YAML frontmatter if present
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                header = parts[1]
                content = parts[2].strip()
                for line in header.strip().splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip().lower()] = v.strip()

        title = meta.get("title") or path.stem.replace("_", " ").title()

        return ExtractedDocument(
            document_id=doc_id,
            file_name=path.name,
            file_path=str(path.resolve()),
            file_type="md",
            file_size_bytes=file_size,
            title=title,
            pages=[ExtractedPage(page_number=1, raw_text=content, char_count=len(content))],
            raw_text=content,
            is_scanned=False,
            metadata=meta,
        )

    @classmethod
    def _extract_docx(cls, path: Path, doc_id: str, file_size: int) -> ExtractedDocument:
        """Extract text from .docx by parsing word/document.xml directly."""
        paragraphs: List[str] = []
        try:
            with zipfile.ZipFile(path) as z:
                xml_content = z.read("word/document.xml")
                root = ET.fromstring(xml_content)
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                for p in root.iter(f"{{{ns['w']}}}p"):
                    texts = [t.text for t in p.iter(f"{{{ns['w']}}}t") if t.text]
                    if texts:
                        paragraphs.append("".join(texts))
        except Exception as e:
            logger.warning(f"Failed to parse docx via zipfile for {path.name}: {e}")
            paragraphs = []

        full_text = "\n\n".join(paragraphs)
        return ExtractedDocument(
            document_id=doc_id,
            file_name=path.name,
            file_path=str(path.resolve()),
            file_type="docx",
            file_size_bytes=file_size,
            title=path.stem.replace("_", " ").title(),
            pages=[ExtractedPage(page_number=1, raw_text=full_text, char_count=len(full_text))],
            raw_text=full_text,
            is_scanned=False,
            metadata={"paragraphs_count": len(paragraphs)},
        )

    @classmethod
    def _extract_json_or_transcript(cls, path: Path, doc_id: str, file_size: int) -> ExtractedDocument:
        """Extracts text from web scrape JSON or YouTube transcript JSON/JSONL."""
        raw_str = path.read_text(encoding="utf-8", errors="replace")
        text_parts = []
        title = path.stem.replace("_", " ").title()
        meta = {}

        if path.suffix.lower() == ".jsonl":
            for line in raw_str.splitlines():
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        t = obj.get("text") or obj.get("content") or obj.get("transcript") or ""
                        if t:
                            text_parts.append(str(t).strip())
                except Exception:
                    pass
        else:
            try:
                data = json.loads(raw_str)
                # YouTube transcript format: list of [{"text": "...", "start": ...}]
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            t = item.get("text") or item.get("content") or item.get("transcript")
                            if t:
                                text_parts.append(str(t).strip())
                # Web scrape format: dict with 'content', 'body', 'text', 'article'
                elif isinstance(data, dict):
                    title = data.get("title") or title
                    t = data.get("content") or data.get("text") or data.get("body") or data.get("article")
                    if t:
                        text_parts.append(str(t).strip())
                    for k, v in data.items():
                        if k not in ("content", "text", "body", "article") and isinstance(v, (str, int, float, bool)):
                            meta[k] = v
            except Exception as e:
                logger.warning(f"Could not parse JSON in {path.name}: {e}")

        full_text = "\n\n".join(text_parts)
        return ExtractedDocument(
            document_id=doc_id,
            file_name=path.name,
            file_path=str(path.resolve()),
            file_type="json",
            file_size_bytes=file_size,
            title=title,
            pages=[ExtractedPage(page_number=1, raw_text=full_text, char_count=len(full_text))],
            raw_text=full_text,
            is_scanned=False,
            metadata=meta,
        )

