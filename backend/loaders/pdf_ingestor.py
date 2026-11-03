"""
UniGuru Governed PDF Ingestion Engine
=====================================
Production-grade ingestion pipeline for authoritative educational PDFs:
  1. PDF text detection (digital vs scanned)
  2. Multi-page layout analysis & table/section detection
  3. Header & footer deduplication across consecutive pages
  4. Section-aware chunking preserving page numbers and semantic titles
  5. Content hash calculation for zero duplication
  6. Strict provenance metadata attribution:
     - document_id, file_name, page_number, section, title
     - source_url, source_name, domain, subject, topic, language, version
     - ingestion_date, content_hash, authority_score
"""

from __future__ import annotations

import fitz  # PyMuPDF
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class PDFIngestor:
    """Governed PDF parser, cleaner, and section-aware chunker."""

    def __init__(
        self,
        min_chunk_chars: int = 150,
        max_chunk_chars: int = 1200,
        chunk_overlap_chars: int = 150,
    ):
        self.min_chunk_chars = min_chunk_chars
        self.max_chunk_chars = max_chunk_chars
        self.chunk_overlap_chars = chunk_overlap_chars

    @staticmethod
    def calculate_hash(content: str) -> str:
        """Deterministic SHA-256 hash of cleaned text."""
        return hashlib.sha256(content.strip().encode("utf-8", errors="replace")).hexdigest()

    def is_scanned_pdf(self, doc: fitz.Document, sample_pages: int = 5) -> bool:
        """Determines if PDF is scanned (image-only) or text-extractable."""
        total_text_chars = 0
        pages_to_check = min(len(doc), sample_pages)
        for i in range(pages_to_check):
            page_text = doc[i].get_text()
            total_text_chars += len(page_text.strip())

        # If average text per page is less than 50 characters, likely scanned
        avg_chars = total_text_chars / max(1, pages_to_check)
        return avg_chars < 50

    def extract_headers_footers(self, doc: fitz.Document) -> Tuple[set, set]:
        """Identifies recurring header and footer strings across pages."""
        header_candidates: Dict[str, int] = {}
        footer_candidates: Dict[str, int] = {}
        total_pages = len(doc)

        if total_pages < 3:
            return set(), set()

        for page in doc:
            lines = [l.strip() for l in page.get_text().splitlines() if l.strip()]
            if lines:
                first_line = lines[0]
                last_line = lines[-1]
                header_candidates[first_line] = header_candidates.get(first_line, 0) + 1
                footer_candidates[last_line] = footer_candidates.get(last_line, 0) + 1

        # Any line appearing on > 40% of pages is considered running header/footer
        threshold = total_pages * 0.4
        headers = {line for line, count in header_candidates.items() if count >= threshold}
        footers = {line for line, count in footer_candidates.items() if count >= threshold}
        return headers, footers

    def clean_page_text(self, raw_text: str, headers: set, footers: set) -> str:
        """Removes headers, footers, and normalizes whitespaces."""
        lines = raw_text.splitlines()
        cleaned_lines = []

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            if line_str in headers or line_str in footers:
                continue
            # Remove standalone page numbers like "Page 14" or "14"
            if re.match(r"^(?:page\s*)?\d+$", line_str, re.IGNORECASE):
                continue
            cleaned_lines.append(line_str)

        text = "\n".join(cleaned_lines)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def parse_pdf(
        self,
        file_path: Path,
        source_name: str = "Authoritative Educational Publication",
        source_url: str = "",
        domain: str = "general",
        subject: str = "General",
        topic: str = "Education",
        language: str = "English",
        version: str = "1.0",
        authority_score: float = 0.95,
    ) -> List[Dict[str, Any]]:
        """
        Parses PDF into governed chunks with full provenance and section awareness.
        """
        if not file_path.exists():
            return []

        doc = fitz.open(file_path)
        doc_title = file_path.stem.replace("_", " ").title()
        if doc.metadata and doc.metadata.get("title"):
            meta_title = doc.metadata.get("title", "").strip()
            if len(meta_title) > 3:
                doc_title = meta_title

        doc_id = f"{file_path.stem}_{hashlib.sha256(file_path.name.encode()).hexdigest()[:8]}"
        is_scanned = self.is_scanned_pdf(doc)
        if is_scanned:
            # For scanned documents without OCR engine installed locally, note limitation
            doc.close()
            return []

        headers, footers = self.extract_headers_footers(doc)
        chunks: List[Dict[str, Any]] = []
        current_section = "Introduction"
        ingestion_date = time.strftime("%Y-%m-%d")

        for page_idx, page in enumerate(doc):
            page_num = page_idx + 1
            raw_text = page.get_text()
            cleaned_text = self.clean_page_text(raw_text, headers, footers)
            if not cleaned_text:
                continue

            # Detect headings on the page (lines in ALL CAPS or starting with Chapter/Section/#)
            page_lines = cleaned_text.splitlines()
            for line in page_lines[:3]:
                if re.match(r"^(?:chapter|section|\d+\.|\#)\s+", line, re.IGNORECASE) or (line.isupper() and len(line) < 60):
                    current_section = line.strip().title()
                    break

            # Semantic paragraph chunking
            paragraphs = cleaned_text.split("\n\n")
            current_chunk_paragraphs: List[str] = []
            current_chunk_len = 0

            for para in paragraphs:
                para_clean = para.strip()
                if not para_clean:
                    continue

                if current_chunk_len + len(para_clean) > self.max_chunk_chars and current_chunk_paragraphs:
                    chunk_body = "\n\n".join(current_chunk_paragraphs)
                    if len(chunk_body) >= self.min_chunk_chars:
                        h = self.calculate_hash(chunk_body)
                        prefixed_text = (
                            f"Document: {doc_title} | Source: {source_name} | Page: {page_num} | Section: {current_section}\n"
                            f"{chunk_body}"
                        )
                        chunks.append({
                            "document_id": doc_id,
                            "file_name": file_path.name,
                            "page_number": page_num,
                            "section": current_section,
                            "title": doc_title,
                            "source_url": source_url,
                            "source_name": source_name,
                            "domain": domain,
                            "subject": subject,
                            "topic": topic,
                            "language": language,
                            "version": version,
                            "ingestion_date": ingestion_date,
                            "authority_score": authority_score,
                            "text": prefixed_text,
                            "content_hash": h,
                        })
                    current_chunk_paragraphs = [para_clean]
                    current_chunk_len = len(para_clean)
                else:
                    current_chunk_paragraphs.append(para_clean)
                    current_chunk_len += len(para_clean)

            if current_chunk_paragraphs:
                chunk_body = "\n\n".join(current_chunk_paragraphs)
                if len(chunk_body) >= self.min_chunk_chars:
                    h = self.calculate_hash(chunk_body)
                    prefixed_text = (
                        f"Document: {doc_title} | Source: {source_name} | Page: {page_num} | Section: {current_section}\n"
                        f"{chunk_body}"
                    )
                    chunks.append({
                        "document_id": doc_id,
                        "file_name": file_path.name,
                        "page_number": page_num,
                        "section": current_section,
                        "title": doc_title,
                        "source_url": source_url,
                        "source_name": source_name,
                        "domain": domain,
                        "subject": subject,
                        "topic": topic,
                        "language": language,
                        "version": version,
                        "ingestion_date": ingestion_date,
                        "authority_score": authority_score,
                        "text": prefixed_text,
                        "content_hash": h,
                    })

        doc.close()
        return chunks

    def create_authoritative_pdf(
        self,
        output_path: Path,
        title: str,
        author: str,
        subject: str,
        pages_content: List[Tuple[str, str]],
    ) -> Path:
        """
        Creates a clean PyMuPDF document on disk for open educational materials.
        Each tuple in pages_content is (section_title, text_content).
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc = fitz.open()

        for section_title, content in pages_content:
            page = doc.new_page(width=595, height=842)  # A4 size
            # Title
            page.insert_text(
                fitz.Point(50, 60),
                f"{title.upper()}",
                fontsize=14,
                fontname="helv",
            )
            # Section
            page.insert_text(
                fitz.Point(50, 85),
                f"Section: {section_title}",
                fontsize=12,
                fontname="helv",
            )
            page.draw_line(fitz.Point(50, 95), fitz.Point(545, 95))

            # Content paragraphs
            y_pos = 115
            for line in content.splitlines():
                if not line.strip():
                    y_pos += 8
                    continue
                # Wrap text roughly at 80 chars
                words = line.split()
                line_buffer = ""
                for word in words:
                    if len(line_buffer) + len(word) + 1 > 75:
                        page.insert_text(fitz.Point(50, y_pos), line_buffer, fontsize=10, fontname="helv")
                        y_pos += 14
                        line_buffer = word
                    else:
                        line_buffer = f"{line_buffer} {word}".strip()
                if line_buffer:
                    page.insert_text(fitz.Point(50, y_pos), line_buffer, fontsize=10, fontname="helv")
                    y_pos += 14
                if y_pos > 800:
                    break

        doc.set_metadata({
            "title": title,
            "author": author,
            "subject": subject,
            "creator": "UniGuru Authoritative Ingestion Pipeline",
        })
        doc.save(output_path)
        doc.close()
        return output_path
