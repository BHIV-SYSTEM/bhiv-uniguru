from __future__ import annotations

import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class AdaptedQuery:
    normalized_query: str
    source_language: str
    target_language: str
    adapter_applied: bool


class LanguageAdapter:
    """
    Translation boundary integration for ecosystem callers.
    Keeps router internals language-agnostic by normalizing input/output.
    """

    def __init__(self) -> None:
        self.enabled = os.getenv("UNIGURU_LANGUAGE_ADAPTER_ENABLED", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.default_language = os.getenv("UNIGURU_LANGUAGE_ADAPTER_DEFAULT_LANGUAGE", "en").strip() or "en"

    _MARATHI_TERMS = {
        "क्वांटम एंटॅंगलमेंट": "quantum entanglement",
        "क्वांटम सुपरपोझिशन": "quantum superposition",
        "अनेकांतवाद": "anekantavada",
        "कर्मयोग": "karma yoga",
        "कर्म योग": "karma yoga",
        "भक्तियोग": "bhakti yoga",
        "भक्ती योग": "bhakti yoga",
        "सोप्या भाषेत": "in simple language",
        "समजावून सांगा": "explain",
        "जैन धर्मातील": "Jain",
        "क्वांटम": "quantum",
        "सुपरपोझिशन": "superposition",
        "एंटॅंगलमेंट": "entanglement",
        "अहिंसा": "ahimsa",
        "ध्यान": "meditation",
        "धर्म": "dharma",
        "कर्म": "karma",
        "योग": "yoga",
        "म्हणजे काय": "what is",
        "म्हणजे": "is",
        "सांगा": "tell",
        "काय": "what",
        "कसे": "how",
        "कसा": "how",
        "फरक": "difference",
    }

    @staticmethod
    def detect_language(query: str, context: Optional[Dict[str, Any]] = None) -> str:
        context_map = dict(context or {})
        explicit_language = str(context_map.get("language") or context_map.get("source_language") or "").strip().lower()
        if explicit_language:
            return explicit_language
        devanagari_count = len(re.findall(r"[\u0900-\u097f]", str(query or "")))
        latin_count = len(re.findall(r"[A-Za-z]", str(query or "")))
        return "mr" if devanagari_count and devanagari_count >= latin_count else "en"

    @classmethod
    def _normalize_marathi_query(cls, query: str) -> str:
        normalized = str(query or "")
        for term, replacement in sorted(cls._MARATHI_TERMS.items(), key=lambda item: len(item[0]), reverse=True):
            normalized = normalized.replace(term, replacement)
        normalized = re.sub(r"[\u0900-\u097f]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        normalized = re.sub(r"\b(?:what\s+){2,}", "what ", normalized, flags=re.IGNORECASE)
        return normalized

    def normalize_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> AdaptedQuery:
        context_map = dict(context or {})
        source_language = self.detect_language(query, context_map) or self.default_language
        if not self.enabled:
            return AdaptedQuery(
                normalized_query=query,
                source_language=source_language,
                target_language=source_language,
                adapter_applied=False,
            )
        normalized_query = self._normalize_marathi_query(query) if source_language == "mr" else query
        return AdaptedQuery(
            normalized_query=normalized_query,
            source_language=source_language,
            target_language="en",
            adapter_applied=source_language != "en",
        )

    def localize_response(
        self,
        response: Dict[str, Any],
        source_language: str,
    ) -> Dict[str, Any]:
        output = dict(response)
        localized = False
        if self.enabled and source_language == "mr" and str(output.get("verification_status") or "").upper() in {
            "VERIFIED", "VERIFIED_PARTIAL", "PARTIAL"
        }:
            trace = output.get("retrieval_trace") or {}
            localized_answer = self._marathi_answer_from_evidence(trace)
            if localized_answer:
                output["answer"] = localized_answer
                localized = True
        output["language_adapter"] = {
            "enabled": self.enabled,
            "source_language": source_language,
            "target_language": "mr" if localized else ("en" if self.enabled else source_language),
            "response_localization_applied": localized,
        }
        return output

    @staticmethod
    def _marathi_answer_from_evidence(trace: Dict[str, Any]) -> Optional[str]:
        kb_root = (Path(__file__).resolve().parents[1] / "knowledge").resolve()
        for evidence in trace.get("evidence_sources", []):
            if not isinstance(evidence, dict):
                continue
            relative_path = str(evidence.get("path") or "").strip()
            if not relative_path:
                continue
            source_path = (kb_root / relative_path).resolve()
            if os.path.commonpath((str(kb_root), str(source_path))) != str(kb_root) or not source_path.is_file():
                continue
            try:
                content = source_path.read_text(encoding="utf-8")
            except OSError:
                continue
            match = re.search(
                r"^## Marathi Summary\s*\n(.*?)(?=^##\s|\Z)",
                content,
                flags=re.MULTILINE | re.DOTALL,
            )
            summary = re.sub(r"\s+", " ", match.group(1)).strip() if match else ""
            if summary:
                citation = relative_path
                if evidence.get("chapter"):
                    citation += f", {evidence['chapter']}"
                return f"{summary}\n\nस्रोत: {citation}"
        return None
