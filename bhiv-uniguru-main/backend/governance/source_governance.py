from __future__ import annotations

import re
from typing import Any, Dict


class SourceGovernance:
    """Deterministic source hierarchy and lineage scoring for Kosha signals."""

    AUTHORITY_ORDER = {
        "canonical_scripture": 1.0,
        "commentary": 0.82,
        "translation": 0.74,
        "ocr_derivative": 0.54,
        "inferred_synthesis": 0.42,
        "unknown": 0.25,
    }

    OCR_MARKERS = ("ocred", "ocr", "scan", "pdf")
    SCRIPTURE_MARKERS = (
        "gita",
        "upanishad",
        "purana",
        "mahabharata",
        "sutra",
        "vachanamrut",
        "shikshapatri",
    )
    COMMENTARY_MARKERS = ("commentary", "bhashya", "vato", "darshan")

    @classmethod
    def assess(cls, signal: Dict[str, Any]) -> Dict[str, Any]:
        source = str(signal.get("source") or "").strip()
        content = str(signal.get("content") or "")
        source_lower = source.lower()
        content_lower = content.lower()

        source_type = "unknown"
        if any(marker in source_lower for marker in cls.OCR_MARKERS):
            source_type = "ocr_derivative"
        if any(marker in source_lower for marker in cls.COMMENTARY_MARKERS):
            source_type = "commentary"
        if any(marker in source_lower for marker in cls.SCRIPTURE_MARKERS) and source_type != "ocr_derivative":
            source_type = "canonical_scripture"
        if "context provided appears" in content_lower or "not provide a comprehensive" in content_lower:
            source_type = "inferred_synthesis"

        integrity_penalty = cls._ocr_integrity_penalty(source=source, content=content)
        authority_weight = round(max(0.0, cls.AUTHORITY_ORDER[source_type] - integrity_penalty), 4)
        confidence_ceiling = cls._confidence_ceiling(source_type=source_type, integrity_penalty=integrity_penalty)

        return {
            "source": source or "unknown",
            "source_type": source_type,
            "authority_weight": authority_weight,
            "confidence_ceiling": confidence_ceiling,
            "ocr_integrity_penalty": round(integrity_penalty, 4),
            "lineage": {
                "original_source": source or "unknown",
                "transformation_history": cls._transformation_history(source_type),
            },
            "suppression_reason": cls._suppression_reason(source_type, authority_weight),
        }

    @classmethod
    def _ocr_integrity_penalty(cls, source: str, content: str) -> float:
        text = f"{source}\n{content}"
        length = max(len(text), 1)
        odd_symbols = len(re.findall(r"[^A-Za-z0-9\u0900-\u097F\s,.;:!?()_\-\[\]/]", text))
        very_short = len(str(content or "").strip()) < 32
        marker_penalty = 0.12 if any(marker in source.lower() for marker in cls.OCR_MARKERS) else 0.0
        short_penalty = 0.16 if very_short else 0.0
        symbol_penalty = min(0.18, odd_symbols / length)
        return min(0.42, marker_penalty + short_penalty + symbol_penalty)

    @staticmethod
    def _confidence_ceiling(source_type: str, integrity_penalty: float) -> float:
        ceilings = {
            "canonical_scripture": 0.95,
            "commentary": 0.88,
            "translation": 0.82,
            "ocr_derivative": 0.72,
            "inferred_synthesis": 0.64,
            "unknown": 0.5,
        }
        ceiling = ceilings.get(source_type, 0.5) - min(0.25, integrity_penalty)
        return round(max(0.25, ceiling), 4)

    @staticmethod
    def _transformation_history(source_type: str) -> list[str]:
        if source_type == "ocr_derivative":
            return ["source_text", "ocr_extraction", "kosha_structuring"]
        if source_type == "inferred_synthesis":
            return ["retrieved_context", "inferred_synthesis", "kosha_structuring"]
        if source_type == "commentary":
            return ["commentarial_source", "kosha_structuring"]
        return ["source_text", "kosha_structuring"]

    @staticmethod
    def _suppression_reason(source_type: str, authority_weight: float) -> str | None:
        if authority_weight < 0.35:
            return f"weak_source_authority:{source_type}"
        return None
