"""
Document Quality Validator for UniGuru Preprocessing Pipeline.
Filters out corrupted OCR, unreadable scans, encoding noise, and empty documents.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class QualityReport:
    passed: bool
    quality_score: float
    reasons: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class QualityValidator:
    """
    Evaluates raw and cleaned text against pedagogical and structural quality gates.
    """

    def __init__(
        self,
        min_char_count: int = 60,
        min_word_count: int = 10,
        min_alphanumeric_ratio: float = 0.50,
        max_repeated_ngram_ratio: float = 0.40,
    ):
        self.min_char_count = min_char_count
        self.min_word_count = min_word_count
        self.min_alphanumeric_ratio = min_alphanumeric_ratio
        self.max_repeated_ngram_ratio = max_repeated_ngram_ratio

    def evaluate(self, text: str, is_scanned_pdf: bool = False) -> QualityReport:
        reasons: List[str] = []
        clean = text.strip()
        char_count = len(clean)

        # 1. Scanned PDF Flag
        if is_scanned_pdf:
            reasons.append("pdf_is_scanned_image_only_requires_ocr")

        # 2. Length Checks
        if char_count < self.min_char_count:
            reasons.append(f"insufficient_characters_{char_count}_lt_{self.min_char_count}")

        # Split words (supporting Devanagari and Latin words)
        words = re.findall(r"[\u0900-\u097F\w]+", clean)
        word_count = len(words)

        if word_count < self.min_word_count:
            reasons.append(f"insufficient_words_{word_count}_lt_{self.min_word_count}")

        if char_count == 0 or word_count == 0:
            return QualityReport(
                passed=False,
                quality_score=0.0,
                reasons=reasons or ["empty_content"],
                metrics={"char_count": 0, "word_count": 0},
            )

        # 3. Alphanumeric / Script Ratio (filtering binary garbage, broken encodings)
        alphanumeric_chars = len(re.findall(r"[\u0900-\u097F\w]", clean))
        alpha_ratio = alphanumeric_chars / char_count
        if alpha_ratio < self.min_alphanumeric_ratio:
            reasons.append(f"low_alphanumeric_ratio_{alpha_ratio:.2f}_lt_{self.min_alphanumeric_ratio}")

        # 4. Check for replacement character noise (\ufffd)
        replacement_count = clean.count("\ufffd")
        if replacement_count > 5:
            reasons.append(f"high_unicode_replacement_characters_{replacement_count}")

        # 5. Check for repetitive word loops (degenerate OCR or scraping loops)
        if word_count >= 20:
            unique_words = len(set(w.lower() for w in words))
            ttr = unique_words / word_count  # Type-Token Ratio
            if ttr < 0.15:
                reasons.append(f"excessive_word_repetition_ttr_{ttr:.2f}")

        # Compute composite quality score (0.0 to 1.0)
        base_score = 1.0
        if is_scanned_pdf:
            base_score -= 0.6
        if alpha_ratio < self.min_alphanumeric_ratio:
            base_score -= 0.3
        if char_count < self.min_char_count * 2:
            base_score -= 0.2
        if len(reasons) > 0:
            base_score -= 0.15 * len(reasons)

        quality_score = round(max(0.0, min(1.0, base_score)), 2)
        passed = (len(reasons) == 0) and (quality_score >= 0.70)

        metrics = {
            "char_count": char_count,
            "word_count": word_count,
            "alphanumeric_ratio": round(alpha_ratio, 2),
            "replacement_chars": replacement_count,
        }

        return QualityReport(
            passed=passed,
            quality_score=quality_score,
            reasons=reasons,
            metrics=metrics,
        )

