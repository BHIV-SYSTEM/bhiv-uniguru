"""Official Balbharati Standards 1-12 Manifest System."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


_CURR = Path(__file__).resolve()
ROOT = _CURR.parents[3]
OFFICIAL_CATALOG_DIR = ROOT / "masterdb" / "balbharti" / "official_catalog"
DEFAULT_MANIFEST_PATH = ROOT / "masterdb" / "balbharti" / "balbharati_manifest.json"

SITE_URL = "https://books.ebalbharati.in/"
PDF_HOST = "https://ebooks.ebalbharati.in/pdfs/"
COVER_HOST = "https://books.ebalbharati.in/BookCovers/"

MEDIUM_NORMALIZATION = {
    "marathi": "Marathi",
    "english": "English",
    "hindi": "Hindi",
    "urdu": "Urdu",
    "gujarati": "Gujarati",
    "kannada": "Kannada",
    "telugu": "Telugu",
    "sanskrit": "Sanskrit",
    "sindhi": "Sindhi",
}


def _sha256(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class BalbharatiManifestBuilder:
    """Discovers and compiles the official Balbharati Standards 1-12 textbook manifest."""

    def __init__(self, catalog_dir: Path = OFFICIAL_CATALOG_DIR) -> None:
        self.catalog_dir = catalog_dir

    def build_manifest(self, year: str = "2026") -> Dict[str, Any]:
        enriched_file = self.catalog_dir / f"year_{year}_catalog_enriched.json"
        standard_file = self.catalog_dir / f"year_{year}_catalog.json"

        catalog_data = None
        if enriched_file.exists():
            catalog_data = json.loads(enriched_file.read_text(encoding="utf-8"))
        elif standard_file.exists():
            catalog_data = json.loads(standard_file.read_text(encoding="utf-8"))
        else:
            # Fallback to the latest available catalog in catalog_dir
            catalog_files = sorted(self.catalog_dir.glob("year_*_catalog*.json"), reverse=True)
            if catalog_files:
                catalog_data = json.loads(catalog_files[0].read_text(encoding="utf-8"))

        books_raw = (catalog_data or {}).get("books", [])
        manifest_books: List[Dict[str, Any]] = []

        for b in books_raw:
            book_id = str(b.get("book_id", "")).strip()
            title = str(b.get("title", "")).strip()
            pdf_name = b.get("pdf_file_name") or f"{book_id}.pdf"
            cover_name = b.get("cover_url", "").split("/")[-1] if b.get("cover_url") else f"{book_id}.jpg"

            # Parse site filter membership if enriched
            filters = b.get("site_filter_membership") or {}
            standards_raw = filters.get("standard", [])
            mediums_raw = filters.get("medium", [])
            subjects_raw = filters.get("subject", [])
            types_raw = filters.get("book_type", [])

            # Determine standard
            standard_val: Optional[int] = None
            for s in standards_raw:
                label = s.get("label", "")
                m = re.search(r"(\d{1,2})", label)
                if m:
                    standard_val = int(m.group(1))
                    break

            if standard_val is None:
                # Infer from title if possible (e.g. "General Science Std 7", "Mathematics Class 5")
                m = re.search(r"\b(?:std|standard|class|grade|इयत्ता|कक्षा)\s*[:\-]?\s*(\d{1,2})\b", title, re.IGNORECASE)
                if m:
                    standard_val = int(m.group(1))

            # Determine mediums
            medium_vals: List[str] = []
            for med in mediums_raw:
                label = str(med.get("label", "")).strip().lower()
                norm = MEDIUM_NORMALIZATION.get(label, label.title())
                if norm not in medium_vals:
                    medium_vals.append(norm)

            if not medium_vals:
                # Infer medium from title or Devanagari script
                devanagari_chars = len(re.findall(r"[\u0900-\u097F]", title))
                if devanagari_chars > 3:
                    medium_vals = ["Marathi"]
                else:
                    medium_vals = ["English"]

            # Determine subject
            subject_val: Optional[str] = None
            if subjects_raw:
                subject_val = subjects_raw[0].get("label", "").strip()
            if not subject_val:
                for subj_candidate in ["Science", "Mathematics", "History", "Geography", "Civics", "English", "Marathi", "Hindi", "EVS"]:
                    if subj_candidate.lower() in title.lower():
                        subject_val = subj_candidate
                        break
            if not subject_val:
                subject_val = "General"

            book_type = types_raw[0].get("label", "Text Book") if types_raw else "Text Book"

            for med_val in medium_vals:
                entry = {
                    "source": "Balbharati",
                    "source_url": f"{SITE_URL}pdfOpen.aspx?itemid={book_id}",
                    "book_url": f"{PDF_HOST}{pdf_name}",
                    "download_tracking_url": f"{SITE_URL}pdfdownload.aspx?itemid={book_id}",
                    "book_id": book_id,
                    "title": title,
                    "standard": standard_val,
                    "medium": med_val,
                    "subject": subject_val,
                    "academic_year": str(year),
                    "book_type": book_type,
                    "cover_url": f"{COVER_HOST}{cover_name}",
                }
                entry["manifest_id"] = f"BALBHARTI_MF_{year}_{book_id}_{med_val.lower()}"
                entry["entry_hash"] = _sha256(entry)
                manifest_books.append(entry)

        standards_represented = sorted(list({b["standard"] for b in manifest_books if b["standard"] is not None}))
        mediums_represented = sorted(list({b["medium"] for b in manifest_books if b["medium"]}))

        summary = {
            "schema_version": "UNIGURU_BALBHARTI_MANIFEST_V1",
            "source": "Official Maharashtra Balbharati eBalbharati Library",
            "source_portal": SITE_URL,
            "academic_year": str(year),
            "total_books_discovered": len(manifest_books),
            "standards_supported": standards_represented,
            "mediums_supported": mediums_represented,
            "licensing_notice": (
                "Official Balbharati digital textbooks are licensed for educational access. "
                "Textbook PDFs must not be committed to Git. Extracted semantic chunks retain full "
                "page and chapter attribution with official links."
            ),
            "books": manifest_books,
        }
        summary["manifest_hash"] = _sha256(summary)
        return summary

    def save_manifest(self, path: Path = DEFAULT_MANIFEST_PATH, year: str = "2026") -> Path:
        manifest = self.build_manifest(year=year)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return path


def load_manifest(path: Path = DEFAULT_MANIFEST_PATH) -> Dict[str, Any]:
    if not path.exists():
        builder = BalbharatiManifestBuilder()
        return builder.build_manifest()
    return json.loads(path.read_text(encoding="utf-8"))
