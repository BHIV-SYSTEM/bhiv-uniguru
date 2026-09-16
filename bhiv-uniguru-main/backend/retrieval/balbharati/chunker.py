"""Chapter-aware hierarchical chunker for Balbharati textbooks with page provenance."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BalbharatiChunk:
    chunk_id: str
    text: str
    page_number: int
    book_title: str
    standard: int
    subject: str
    medium: str
    chapter: str
    section: Optional[str] = None
    content_type: str = "text"  # text | table | definition | exercise | diagram_caption | example
    source_url: str = ""
    source_type: str = "Balbharati"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "page_number": self.page_number,
            "book_title": self.book_title,
            "standard": self.standard,
            "subject": self.subject,
            "medium": self.medium,
            "chapter": self.chapter,
            "section": self.section,
            "content_type": self.content_type,
            "source_url": self.source_url,
            "source_type": self.source_type,
            "metadata": self.metadata,
        }


def _make_chunk_id(book_title: str, standard: int, subject: str, page: int, idx: int) -> str:
    raw = f"{book_title}_{standard}_{subject}_{page}_{idx}"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    clean_sub = re.sub(r"[^a-zA-Z0-9]", "", subject).lower()[:6]
    return f"bb_s{standard}_{clean_sub}_p{page}_{idx}_{h}"


class HierarchicalChunker:
    """Chunks textbook content semantically while preserving hierarchy, tables, and page attribution."""

    def __init__(self, target_chunk_size: int = 500, max_chunk_size: int = 1000, overlap: int = 80) -> None:
        self.target_chunk_size = target_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    def detect_chapter(self, page_text: str, current_chapter: str = "General") -> str:
        lines = [line.strip() for line in page_text.splitlines() if line.strip()]
        for line in lines[:5]:
            # e.g., "1. The Living World : Adaptations and Classification"
            # "Chapter 2 - Plants: Structure and Function"
            # "धडा १ : सजीव सृष्टी : अनुकूलन व वर्गीकरण"
            # "प्रकरण ३: बल व दाब"
            m = re.match(r"^(?:(?:chapter|lesson|unit|धडा|प्रकरण)\s*\d+[\.\:\-]?|\d+[\.\:\-])\s*([A-Za-z0-9\u0900-\u097F\s\:\,\-]{3,60})$", line, re.IGNORECASE)
            if m:
                return m.group(0).strip()
        return current_chapter

    def detect_sections(self, text: str) -> List[Dict[str, Any]]:
        """Splits page text into logical structural elements (tables, exercises, definitions, paragraphs)."""
        blocks: List[Dict[str, Any]] = []
        lines = text.splitlines()
        current_block: List[str] = []
        current_type = "text"

        def flush():
            nonlocal current_block, current_type
            if current_block:
                joined = "\n".join(current_block).strip()
                if joined:
                    blocks.append({"type": current_type, "text": joined})
                current_block = []
                current_type = "text"

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current_type == "text" and len("\n".join(current_block)) > self.target_chunk_size:
                    flush()
                continue

            # Table row detection (markdown table format or tab/pipe separated)
            if "|" in stripped or "\t" in line:
                if current_type != "table":
                    flush()
                    current_type = "table"
                current_block.append(stripped)
                continue
            elif current_type == "table":
                flush()

            # Exercise / Questions detection
            if re.match(r"^(?:exercises|questions|स्वाध्याय|प्रश्न)\b", stripped, re.IGNORECASE) or re.match(r"^\d+[\.\)]\s*(?:what|why|how|explain|find|write|fill|कोण|काय|कसे|स्पष्ट करा)", stripped, re.IGNORECASE):
                if current_type != "exercise":
                    flush()
                    current_type = "exercise"
                current_block.append(stripped)
                continue

            # Definition detection
            if re.match(r"^(?:definition|व्याख्या|अर्थ)\s*[:\-]", stripped, re.IGNORECASE) or re.search(r"\b(?:is defined as|म्हणजे|म्हणतात)\b", stripped, re.IGNORECASE):
                if current_type == "text" and len(current_block) > 2:
                    flush()
                current_type = "definition"
                current_block.append(stripped)
                continue

            # Diagram / figure caption detection
            if re.match(r"^(?:fig(?:ure)?\.?|आकृती|चित्र)\s*\d+[\.\:]?", stripped, re.IGNORECASE):
                flush()
                blocks.append({"type": "diagram_caption", "text": stripped})
                continue

            current_block.append(stripped)

        flush()
        return blocks

    def chunk_page(
        self,
        page_text: str,
        page_number: int,
        book_title: str,
        standard: int,
        subject: str,
        medium: str,
        chapter: str,
        source_url: str = "",
    ) -> List[BalbharatiChunk]:
        """Convert a page's content into semantic chunks preserving parent context."""
        blocks = self.detect_sections(page_text)
        chunks: List[BalbharatiChunk] = []
        chunk_idx = 1

        for block in blocks:
            b_type = block["type"]
            b_text = block["text"]

            # Units like tables, definitions, and diagram captions should stay whole if possible
            if b_type in {"table", "definition", "diagram_caption"} or len(b_text) <= self.max_chunk_size:
                # Prepend parent context header so chunk is not isolated
                header = f"Book: Standard {standard} {subject} ({book_title}) | Chapter: {chapter} | Page: {page_number}"
                if b_type == "diagram_caption":
                    formatted_text = f"[{header}]\n[Diagram Caption]: {b_text}"
                elif b_type == "table":
                    formatted_text = f"[{header}]\n[Structured Table]:\n{b_text}"
                else:
                    formatted_text = f"[{header}]\n{b_text}"

                chunk_id = _make_chunk_id(book_title, standard, subject, page_number, chunk_idx)
                chunks.append(
                    BalbharatiChunk(
                        chunk_id=chunk_id,
                        text=formatted_text,
                        page_number=page_number,
                        book_title=book_title,
                        standard=standard,
                        subject=subject,
                        medium=medium,
                        chapter=chapter,
                        content_type=b_type,
                        source_url=source_url,
                        metadata={"block_type": b_type, "raw_length": len(b_text)},
                    )
                )
                chunk_idx += 1
            else:
                # Split large text paragraphs along sentence boundaries
                sentences = re.split(r"(?<=[.!?।])\s+", b_text)
                cur_parts: List[str] = []
                cur_len = 0

                for sent in sentences:
                    s_clean = sent.strip()
                    if not s_clean:
                        continue
                    if cur_len + len(s_clean) > self.max_chunk_size and cur_parts:
                        body = " ".join(cur_parts)
                        header = f"Book: Standard {standard} {subject} ({book_title}) | Chapter: {chapter} | Page: {page_number}"
                        formatted_text = f"[{header}]\n{body}"
                        chunk_id = _make_chunk_id(book_title, standard, subject, page_number, chunk_idx)
                        chunks.append(
                            BalbharatiChunk(
                                chunk_id=chunk_id,
                                text=formatted_text,
                                page_number=page_number,
                                book_title=book_title,
                                standard=standard,
                                subject=subject,
                                medium=medium,
                                chapter=chapter,
                                content_type=b_type,
                                source_url=source_url,
                                metadata={"block_type": b_type, "raw_length": len(body)},
                            )
                        )
                        chunk_idx += 1
                        # Overlap: keep last sentence
                        cur_parts = [cur_parts[-1], s_clean] if len(cur_parts) > 1 else [s_clean]
                        cur_len = sum(len(p) for p in cur_parts)
                    else:
                        cur_parts.append(s_clean)
                        cur_len += len(s_clean)

                if cur_parts:
                    body = " ".join(cur_parts)
                    header = f"Book: Standard {standard} {subject} ({book_title}) | Chapter: {chapter} | Page: {page_number}"
                    formatted_text = f"[{header}]\n{body}"
                    chunk_id = _make_chunk_id(book_title, standard, subject, page_number, chunk_idx)
                    chunks.append(
                        BalbharatiChunk(
                            chunk_id=chunk_id,
                            text=formatted_text,
                            page_number=page_number,
                            book_title=book_title,
                            standard=standard,
                            subject=subject,
                            medium=medium,
                            chapter=chapter,
                            content_type=b_type,
                            source_url=source_url,
                            metadata={"block_type": b_type, "raw_length": len(body)},
                        )
                    )
                    chunk_idx += 1

        return chunks
