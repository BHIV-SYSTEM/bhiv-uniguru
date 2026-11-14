from __future__ import annotations

import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class AdaptedQuery:
    normalized_query: str
    source_language: str
    target_language: str
    adapter_applied: bool


class LanguageAdapter:
    """
    Translation and language boundary integration for UniGuru.
    Implements strict priority:
      1. Explicit language requested by user in query.
      2. Explicit language selected in application context.
      3. Language detected from message script.
      4. Documented default ('en').
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

    _EXPLICIT_EN_PATTERNS = (
        r"\b(?:in\s+english|to\s+english|into\s+english|explain\s+(?:this\s+)?in\s+english|in\s+the\s+english\s+language)\b",
        r"(?:इंग्रजीत|इंग्लिशमध्ये|इंग्लिश\s+मध्ये|english\s+मध्ये|english\s+त|इंग्रजी\s+भाषेत)",
    )
    _EXPLICIT_MR_PATTERNS = (
        r"\b(?:in\s+marathi|to\s+marathi|into\s+marathi|explain\s+(?:this\s+)?in\s+marathi|in\s+the\s+marathi\s+language)\b",
        r"(?:मराठीत|मराठीमध्ये|मराठी\s+मध्ये|मराठी\s+भाषेत)",
    )

    @classmethod
    def resolve_languages(cls, query: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
        """
        Determine (source_language, target_language) following strict Section 3.B priority:
          1. Explicit language requested by user in query.
          2. Explicit language selected in application context.
          3. Language detected from message script.
          4. Default language ('en').
        """
        context_map = dict(context or {})
        text = str(query or "").strip().lower()

        # Step 3: Script detection for input source language
        devanagari_count = len(re.findall(r"[\u0900-\u097f]", query or ""))
        latin_count = len(re.findall(r"[A-Za-z]", query or ""))
        detected_source = "mr" if devanagari_count and devanagari_count >= latin_count else "en"

        # Step 1: Explicit language requested by user in query
        explicit_target: Optional[str] = None
        for pattern in cls._EXPLICIT_EN_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                explicit_target = "en"
                break
        if not explicit_target:
            for pattern in cls._EXPLICIT_MR_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    explicit_target = "mr"
                    break

        # Step 2: Explicit language selected in application context
        if not explicit_target:
            ctx_lang = str(context_map.get("target_language") or context_map.get("language") or context_map.get("ui_language") or "").strip().lower()
            if ctx_lang in {"en", "english"}:
                explicit_target = "en"
            elif ctx_lang in {"mr", "marathi"}:
                explicit_target = "mr"

        # Step 3 / 4: Target defaults to detected source language, or application default
        target_language = explicit_target or detected_source or "en"
        return detected_source, target_language

    def detect_language(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Backward-compatible helper returning source language."""
        src, _ = self.resolve_languages(query, context)
        return src

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
        source_language, target_language = self.resolve_languages(query, context_map)
        if not self.enabled:
            return AdaptedQuery(
                normalized_query=query,
                source_language=source_language,
                target_language=target_language,
                adapter_applied=False,
            )
        normalized_query = self._normalize_marathi_query(query) if source_language == "mr" else query
        return AdaptedQuery(
            normalized_query=normalized_query,
            source_language=source_language,
            target_language=target_language,
            adapter_applied=source_language != "en",
        )

    def localize_response(
        self,
        response: Dict[str, Any],
        source_language: str,
        target_language: Optional[str] = None,
    ) -> Dict[str, Any]:
        output = dict(response)
        effective_target = target_language or source_language
        localized = False
        v_status = str(output.get("verification_status") or "").upper()

        if self.enabled and effective_target == "mr" and v_status in {"VERIFIED", "VERIFIED_PARTIAL", "PARTIAL"}:
            trace = output.get("retrieval_trace") or {}
            localized_answer = self._marathi_answer_from_evidence(trace)
            if not localized_answer and output.get("answer"):
                # If evidence/answer is primarily English, localize to Marathi via LLM service
                lat_chars = len(re.findall(r"[A-Za-z]", output["answer"]))
                dev_chars = len(re.findall(r"[\u0900-\u097f]", output["answer"]))
                if lat_chars > dev_chars:
                    try:
                        import requests
                        llm_url = os.environ.get("UNIGURU_LLM_URL", "http://127.0.0.1:8001/generate")
                        prompt = f"खालील माहितीचा मराठीत स्पष्ट आणि सोप्या भाषेत अनुवाद किंवा स्पष्टीकरण द्या:\n\n{output['answer'][:1200]}"
                        res = requests.post(
                            llm_url,
                            json={"query": prompt, "language": "mr", "max_new_tokens": 300},
                            timeout=15,
                        )
                        if res.status_code == 200:
                            candidate = res.json().get("answer", "").strip()
                            if candidate:
                                localized_answer = candidate
                    except Exception:
                        pass
            if localized_answer:
                output["answer"] = localized_answer
                localized = True
        elif self.enabled and effective_target == "en" and v_status in {"VERIFIED", "VERIFIED_PARTIAL", "PARTIAL"}:
            if output.get("answer"):
                lat_chars = len(re.findall(r"[A-Za-z]", output["answer"]))
                dev_chars = len(re.findall(r"[\u0900-\u097f]", output["answer"]))
                if dev_chars > lat_chars:
                    try:
                        import requests
                        llm_url = os.environ.get("UNIGURU_LLM_URL", "http://127.0.0.1:8001/generate")
                        prompt = f"Explain the following information clearly and accurately in English:\n\n{output['answer'][:1200]}"
                        res = requests.post(
                            llm_url,
                            json={"query": prompt, "language": "en", "max_new_tokens": 300},
                            timeout=15,
                        )
                        if res.status_code == 200:
                            candidate = res.json().get("answer", "").strip()
                            if candidate:
                                output["answer"] = candidate
                                localized = True
                    except Exception:
                        pass

        output["language_adapter"] = {
            "enabled": self.enabled,
            "source_language": source_language,
            "target_language": effective_target,
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
                re.MULTILINE | re.DOTALL,
            )
            if match:
                candidate = match.group(1).strip()
                if candidate:
                    return candidate
        return None
