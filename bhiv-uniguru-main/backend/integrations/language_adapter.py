from __future__ import annotations

import os
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

    def normalize_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> AdaptedQuery:
        context_map = dict(context or {})
        source_language = str(context_map.get("language") or context_map.get("source_language") or self.default_language).strip().lower()
        if not self.enabled:
            return AdaptedQuery(
                normalized_query=query,
                source_language=source_language,
                target_language=source_language,
                adapter_applied=False,
            )
        # Safe compatibility mode: query content is preserved unless an external translator is configured.
        return AdaptedQuery(
            normalized_query=query,
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
        output["language_adapter"] = {
            "enabled": self.enabled,
            "source_language": source_language,
            "target_language": "en" if self.enabled else source_language,
            "response_localization_applied": False,
        }
        return output
