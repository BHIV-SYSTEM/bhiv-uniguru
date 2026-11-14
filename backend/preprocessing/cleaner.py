"""
Universal Text Cleaner for UniGuru Ingestion Pipeline.
Removes headers, footers, OCR artifacts, control characters, and normalizes typography.
"""
from __future__ import annotations

import html
import re
import unicodedata
from typing import Dict, List, Optional, Set, Tuple


class TextCleaner:
    """
    Cleans raw extracted text across educational PDFs, documents, web pages, and transcripts.
    """

    # Matches standalone page numbers: '12', 'Page 12', '- 12 -', '[12]'
    PAGE_NUMBER_REGEX = re.compile(
        r"^(?:(?:page|पृष्ठ|पान)\s*)?[-–—\[(]*\s*\d+\s*[-–—\])]*$",
        re.IGNORECASE | re.MULTILINE,
    )

    # Broken hyphenation across line breaks: 'exam-\nple' -> 'example'
    HYPHENATION_REGEX = re.compile(r"(\w+)[-–]\n\s*(\w+)")

    # Control characters excluding standard newline (\n), tab (\t), and carriage return (\r)
    CONTROL_CHAR_REGEX = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ufffd]")

    # HTML tags
    HTML_TAG_REGEX = re.compile(r"<[^>]+>")

    @classmethod
    def clean(
        cls,
        text: str,
        headers: Optional[Set[str]] = None,
        footers: Optional[Set[str]] = None,
    ) -> str:
        """
        Full cleaning pipeline for raw document text.
        """
        if not text:
            return ""

        headers = headers or set()
        footers = footers or set()

        # 1. Unicode normalization (NFKC)
        cleaned = unicodedata.normalize("NFKC", text)

        # 2. Unescape HTML entities & strip tags
        cleaned = html.unescape(cleaned)
        cleaned = cls.HTML_TAG_REGEX.sub(" ", cleaned)

        # 3. Strip control characters
        cleaned = cls.CONTROL_CHAR_REGEX.sub(" ", cleaned)

        # 4. Fix broken hyphenated line-breaks (e.g. 'com-\nputer' -> 'computer')
        cleaned = cls.HYPHENATION_REGEX.sub(r"\1\2", cleaned)

        # 5. Line-by-line filtering (headers, footers, standalone page numbers)
        lines = cleaned.splitlines()
        filtered_lines = []

        for line in lines:
            line_str = line.strip()
            if not line_str:
                filtered_lines.append("")
                continue

            # Strip recurring headers and footers
            if line_str in headers or line_str in footers:
                continue

            # Strip standalone page numbering lines
            if cls.PAGE_NUMBER_REGEX.match(line_str):
                continue

            # Strip horizontal divider lines (e.g. '------', '======')
            if re.match(r"^[-=_*~]{3,}$", line_str):
                continue

            filtered_lines.append(line_str)

        cleaned = "\n".join(filtered_lines)

        # 6. Normalize whitespace
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        # Collapse 3 or more newlines into double newlines
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        return cleaned.strip()

    @classmethod
    def identify_recurring_headers_footers(
        cls, page_texts: List[str], occurrence_threshold: float = 0.4
    ) -> Tuple[Set[str], Set[str]]:
        """
        Identify recurring headers and footers across multiple pages of a document.
        """
        if len(page_texts) < 3:
            return set(), set()

        header_counts: Dict[str, int] = {}
        footer_counts: Dict[str, int] = {}
        total_pages = len(page_texts)

        for text in page_texts:
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            if lines:
                first_line = lines[0]
                last_line = lines[-1]
                header_counts[first_line] = header_counts.get(first_line, 0) + 1
                footer_counts[last_line] = footer_counts.get(last_line, 0) + 1

        min_occurrences = max(2, int(total_pages * occurrence_threshold))
        headers = {line for line, cnt in header_counts.items() if cnt >= min_occurrences}
        footers = {line for line, cnt in footer_counts.items() if cnt >= min_occurrences}

        return headers, footers
