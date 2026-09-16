"""PDF Ingestion and Text Extraction Pipeline with Scanned Page Detection and OCR Fallback."""

from __future__ import annotations

import logging
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

logger = logging.getLogger("uniguru.balbharati.pdf")


class PDFIngestionPipeline:
    def __init__(self, enable_ocr: bool = True, min_native_text_chars: int = 50) -> None:
        self.enable_ocr = enable_ocr
        self.min_native_text_chars = min_native_text_chars
        self._fitz = None

    def _get_fitz(self):
        if self._fitz is None:
            try:
                import fitz
                self._fitz = fitz
            except ImportError as exc:
                raise RuntimeError("PyMuPDF (fitz) is required for PDF ingestion. Run `pip install PyMuPDF`.") from exc
        return self._fitz

    def validate_pdf(self, pdf_path: str | Path) -> Tuple[bool, str]:
        path = Path(pdf_path)
        if not path.exists():
            return False, f"File does not exist: {path}"
        if path.stat().st_size < 1024:
            return False, f"PDF file too small or corrupted: {path.stat().st_size} bytes"

        try:
            with open(path, "rb") as f:
                header = f.read(5)
                if not header.startswith(b"%PDF-"):
                    return False, f"Invalid PDF header: {header}"
        except Exception as exc:
            return False, f"Failed to read PDF file: {exc}"

        fitz = self._get_fitz()
        try:
            doc = fitz.open(str(path))
            page_count = len(doc)
            doc.close()
            if page_count == 0:
                return False, "PDF contains 0 pages."
            return True, f"Valid PDF with {page_count} pages."
        except Exception as exc:
            return False, f"PyMuPDF failed to open PDF: {exc}"

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        norm = unicodedata.normalize("NFC", text)
        # Fix hyphens at end of lines
        norm = re.sub(r"(\w+)-\n(\w+)", r"\1\2", norm)
        # Normalize excessive whitespace but preserve single newlines
        norm = re.sub(r"[ \t]+", " ", norm)
        norm = re.sub(r"\n{3,}", "\n\n", norm)
        return norm.strip()

    def _ocr_page(self, page) -> str:
        """Fallback OCR for scanned pages using pytesseract if available."""
        if not self.enable_ocr:
            return ""
        try:
            import pytesseract
            from PIL import Image
            import io

            pix = page.get_pixmap(dpi=150)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img, lang="mar+hin+eng")
            return self.clean_text(text)
        except Exception as exc:
            logger.debug(f"OCR fallback failed or unavailable: {exc}")
            return ""

    def process_pdf(
        self,
        pdf_path: str | Path,
        start_page: int = 1,
        max_pages: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Extracts text page by page, detecting scanned pages and falling back to OCR when needed."""
        fitz = self._get_fitz()
        path = Path(pdf_path)
        valid, msg = self.validate_pdf(path)
        if not valid:
            raise ValueError(f"PDF validation failed for {path}: {msg}")

        doc = fitz.open(str(path))
        try:
            total_pages = len(doc)
            end_page = min(total_pages, start_page + max_pages - 1) if max_pages else total_pages

            for page_idx in range(start_page - 1, end_page):
                page = doc[page_idx]
                page_num = page_idx + 1

                # 1. Try native text extraction
                native_text = self.clean_text(page.get_text("text"))
                is_scanned = len(native_text) < self.min_native_text_chars

                extracted_text = native_text
                ocr_applied = False

                # 2. Fallback to OCR if scanned and native text failed
                if is_scanned and self.enable_ocr:
                    ocr_text = self._ocr_page(page)
                    if len(ocr_text) > len(native_text):
                        extracted_text = ocr_text
                        ocr_applied = True

                yield {
                    "page_number": page_num,
                    "text": extracted_text,
                    "is_scanned": is_scanned,
                    "ocr_applied": ocr_applied,
                    "char_count": len(extracted_text),
                }
        finally:
            doc.close()
