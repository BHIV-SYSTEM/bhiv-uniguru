"""
UniGuru Master Preprocessing Pipeline.
Orchestrates:
  1. Extraction (PDF, DOCX, TXT, MD, JSON) -> backend/data/extracted/
  2. Text Cleaning -> backend/data/cleaned/
  3. Deduplication Check (SHA-256 & Shingling)
  4. Language Detection (Marathi, Hindi, English, Sanskrit)
  5. Quality Validation (Rejections -> backend/data/rejected/)
  6. Metadata Generation -> backend/data/processed/
  7. Semantic Chunking -> backend/data/chunks/
  8. Export for RAG & Qwen 2.5 LLM Fine-Tuning
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.preprocessing.chunker import TextChunk, TextChunker
from backend.preprocessing.cleaner import TextCleaner
from backend.preprocessing.deduplicator import DocumentDeduplicator
from backend.preprocessing.extractor import DocumentExtractor, ExtractedDocument
from backend.preprocessing.language_detector import LanguageDetector
from backend.preprocessing.validator import QualityReport, QualityValidator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("uniguru.preprocessing.pipeline")


class PreprocessingPipeline:
    """
    Manages the end-to-end data preparation lifecycle for UniGuru.
    """

    def __init__(
        self,
        base_data_dir: Optional[str | Path] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
    ):
        self.base_dir = Path(base_data_dir) if base_data_dir else (_PROJECT_ROOT / "backend" / "data")
        self.raw_dir = self.base_dir / "raw"
        self.extracted_dir = self.base_dir / "extracted"
        self.cleaned_dir = self.base_dir / "cleaned"
        self.processed_dir = self.base_dir / "processed"
        self.chunks_dir = self.base_dir / "chunks"
        self.rejected_dir = self.base_dir / "rejected"

        # Ensure all directories exist
        for d in (
            self.raw_dir,
            self.extracted_dir,
            self.cleaned_dir,
            self.processed_dir,
            self.chunks_dir,
            self.rejected_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)

        self.cleaner = TextCleaner()
        self.deduplicator = DocumentDeduplicator(self.processed_dir / "dedup_registry.json")
        self.validator = QualityValidator()
        self.chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def process_file(
        self,
        file_path: str | Path,
        domain_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute full 7-stage preprocessing on a single input file.
        """
        path = Path(file_path)
        logger.info(f"Processing: {path.name}")
        t0 = time.time()

        # Stage 1: Extraction
        try:
            extracted_doc = DocumentExtractor.extract(path)
        except Exception as e:
            logger.error(f"Extraction failed for {path.name}: {e}")
            self._save_rejection(path.name, f"extraction_error: {str(e)}")
            return {"status": "rejected", "file": path.name, "reason": str(e)}

        doc_id = extracted_doc.document_id

        # Persist extracted artifacts
        extracted_json_path = self.extracted_dir / f"{doc_id}.json"
        extracted_txt_path = self.extracted_dir / f"{doc_id}.txt"
        extracted_json_path.write_text(json.dumps(extracted_doc.to_dict(), indent=2), encoding="utf-8")
        extracted_txt_path.write_text(extracted_doc.raw_text, encoding="utf-8")

        # Stage 2: Header/Footer Detection & Cleaning
        page_texts = [p.raw_text for p in extracted_doc.pages]
        headers, footers = self.cleaner.identify_recurring_headers_footers(page_texts)
        cleaned_text = self.cleaner.clean(extracted_doc.raw_text, headers=headers, footers=footers)

        # Persist cleaned text
        cleaned_payload = {
            "document_id": doc_id,
            "file_name": path.name,
            "cleaned_text": cleaned_text,
            "char_count": len(cleaned_text),
            "headers_removed": list(headers),
            "footers_removed": list(footers),
        }
        (self.cleaned_dir / f"{doc_id}.json").write_text(
            json.dumps(cleaned_payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Stage 3: Deduplication Check
        is_dup, orig_doc_id, match_type = self.deduplicator.check_duplicate(
            cleaned_text, document_id=doc_id, file_name=path.name
        )
        if is_dup:
            logger.warning(f"Duplicate detected: {path.name} is a duplicate of {orig_doc_id} ({match_type})")
            self._save_rejection(path.name, f"duplicate_document: matches_{orig_doc_id}_{match_type}")
            return {
                "status": "duplicate",
                "document_id": doc_id,
                "file": path.name,
                "duplicate_of": orig_doc_id,
            }

        # Stage 4: Language Detection (Marathi, Hindi, English, Sanskrit)
        lang_result = LanguageDetector.detect(cleaned_text)
        detected_lang = lang_result["language"]
        lang_conf = lang_result["confidence"]

        # Stage 5: Quality Validation Gate
        quality = self.validator.evaluate(cleaned_text, is_scanned_pdf=extracted_doc.is_scanned)
        if not quality.passed:
            logger.warning(f"Quality validation failed for {path.name}: {quality.reasons}")
            self._save_rejection(path.name, f"quality_rejection: {','.join(quality.reasons)}", metrics=quality.metrics)
            return {
                "status": "rejected",
                "document_id": doc_id,
                "file": path.name,
                "reasons": quality.reasons,
                "metrics": quality.metrics,
            }

        # Inferred domain
        domain = domain_hint or self._infer_domain(path.name, cleaned_text)

        # Stage 6: Metadata Generation & Processed Record
        metadata = {
            "document_id": doc_id,
            "file_name": path.name,
            "file_path": str(path.resolve()),
            "title": extracted_doc.title,
            "file_type": extracted_doc.file_type,
            "file_size_bytes": extracted_doc.file_size_bytes,
            "language": detected_lang,
            "language_confidence": lang_conf,
            "domain": domain,
            "quality_score": quality.quality_score,
            "char_count": len(cleaned_text),
            "word_count": quality.metrics.get("word_count", 0),
            "total_pages": len(extracted_doc.pages),
            "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "sha256": self.deduplicator.calculate_sha256(cleaned_text),
        }
        (self.processed_dir / f"{doc_id}.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Stage 7: Semantic Chunking
        chunks = self.chunker.chunk_document(
            text=cleaned_text,
            document_id=doc_id,
            language=detected_lang,
            domain=domain,
            source_metadata={
                "source_file": path.name,
                "title": extracted_doc.title,
                "domain": domain,
                "language": detected_lang,
            },
        )

        # Persist Chunks in JSON and JSONL formats
        chunks_json_path = self.chunks_dir / f"{doc_id}_chunks.json"
        chunks_jsonl_path = self.chunks_dir / f"{doc_id}_chunks.jsonl"
        
        chunks_data = [c.to_dict() for c in chunks]
        chunks_json_path.write_text(json.dumps(chunks_data, indent=2, ensure_ascii=False), encoding="utf-8")
        with chunks_jsonl_path.open("w", encoding="utf-8") as f:
            for c in chunks_data:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")

        elapsed = round(time.time() - t0, 3)
        logger.info(
            f"Successfully processed {path.name} in {elapsed}s: "
            f"{len(chunks)} chunks, language={detected_lang} ({lang_conf:.2f}), domain={domain}"
        )

        # Update deduplication registry on disk
        self.deduplicator.save_registry()

        return {
            "status": "success",
            "document_id": doc_id,
            "file": path.name,
            "language": detected_lang,
            "domain": domain,
            "chunks_count": len(chunks),
            "processing_time_s": elapsed,
        }

    def process_all_raw(self, domain_hint: Optional[str] = None) -> List[Dict[str, Any]]:
        """Process all supported files inside backend/data/raw/."""
        supported_exts = {".pdf", ".txt", ".md", ".docx", ".json", ".jsonl"}
        results = []

        files = [
            f
            for f in self.raw_dir.glob("*")
            if f.is_file() and f.suffix.lower() in supported_exts and not f.name.startswith(".")
        ]

        logger.info(f"Discovered {len(files)} files in {self.raw_dir}")
        for file in files:
            res = self.process_file(file, domain_hint=domain_hint)
            results.append(res)

        return results

    def export_fine_tuning_dataset(
        self,
        output_file: Optional[str | Path] = None,
        min_chunk_len: int = 150,
    ) -> Path:
        """
        Export processed chunks into a JSONL fine-tuning dataset formatted for Qwen 2.5 7B.
        Format: {"context": ..., "question": ..., "answer": ...}
        """
        out_path = Path(output_file) if output_file else (self.processed_dir / "fine_tuning_rag.jsonl")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        exported_count = 0
        with out_path.open("w", encoding="utf-8") as out_f:
            for chunk_file in self.chunks_dir.glob("*_chunks.jsonl"):
                with chunk_file.open("r", encoding="utf-8") as in_f:
                    for line in in_f:
                        if not line.strip():
                            continue
                        chunk = json.loads(line)
                        text = chunk.get("text", "").strip()
                        if len(text) < min_chunk_len:
                            continue

                        # Extract first sentence or title as query trigger
                        sentences = [s.strip() for s in text.splitlines() if s.strip()]
                        topic = chunk.get("metadata", {}).get("title") or chunk.get("domain", "General")
                        question = f"What key information is provided regarding {topic}?"

                        record = {
                            "context": text,
                            "question": question,
                            "answer": text,
                        }
                        out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        exported_count += 1

        logger.info(f"Exported {exported_count} training pairs to {out_path.resolve()}")
        return out_path

    def _save_rejection(self, file_name: str, reason: str, metrics: Optional[Dict[str, Any]] = None) -> None:
        report = {
            "file_name": file_name,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "reason": reason,
            "metrics": metrics or {},
        }
        rej_file = self.rejected_dir / f"{file_name}_rejected.json"
        rej_file.write_text(json.dumps(report, indent=2), encoding="utf-8")

    @staticmethod
    def _infer_domain(file_name: str, text: str) -> str:
        name_lower = file_name.lower()
        text_sample = text[:1500].lower()

        if any(k in name_lower or k in text_sample for k in ("math", "गणित", "calculus", "algebra", "arithmetic")):
            return "mathematics"
        if any(k in name_lower or k in text_sample for k in ("physic", "भौतिक", "electromagnetism", "gravity", "force")):
            return "physics"
        if any(k in name_lower or k in text_sample for k in ("sanskrit", "संस्कृत", "panini", "sutra", "shloka", "वेद")):
            return "sanskrit"
        if any(k in name_lower or k in text_sample for k in ("history", "इतिहास", "civilisation", "empire", "ancient")):
            return "history"
        if any(k in name_lower or k in text_sample for k in ("bio", "जीवशास्त्र", "mitochondria", "cell", "plant")):
            return "biology"
        if any(k in name_lower or k in text_sample for k in ("agri", "शेती", "irrigation", "crop", "soil")):
            return "agriculture"
        return "general"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="UniGuru Educational Data Preprocessing Pipeline")
    parser.add_argument("--input-dir", type=str, default=None, help="Directory containing raw documents")
    parser.add_argument("--file", type=str, default=None, help="Process a single file")
    parser.add_argument("--domain", type=str, default=None, help="Explicit domain hint")
    parser.add_argument("--export-fine-tuning", action="store_true", help="Generate fine_tuning_rag.jsonl")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pipeline = PreprocessingPipeline()

    if args.file:
        res = pipeline.process_file(args.file, domain_hint=args.domain)
        print(json.dumps(res, indent=2))
    else:
        results = pipeline.process_all_raw(domain_hint=args.domain)
        print(f"\nCompleted processing {len(results)} files.")
        successes = sum(1 for r in results if r.get("status") == "success")
        dups = sum(1 for r in results if r.get("status") == "duplicate")
        rejected = sum(1 for r in results if r.get("status") == "rejected")
        print(f"Summary: {successes} succeeded, {dups} duplicates skipped, {rejected} rejected.")

    if args.export_fine_tuning:
        pipeline.export_fine_tuning_dataset()


if __name__ == "__main__":
    main()

