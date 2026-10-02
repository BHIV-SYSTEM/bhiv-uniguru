from __future__ import annotations

import re
from enum import Enum


class QueryType(str, Enum):
    KNOWLEDGE_QUERY = "knowledge_query"
    CONCEPT_QUERY = "concept_query"
    EXPLANATION_QUERY = "explanation_query"
    WEB_LOOKUP = "web_lookup"


_WEB_LOOKUP_PATTERNS = (
    r"\btoday\b",
    r"\blatest\b",
    r"\bcurrent\b",
    r"\brecent\b",
    r"\bnews\b",
    r"\bweather\b",
    r"\bmarket\b",
    r"\bprice\b",
    r"\bscore\b",
    # A "capital of" question requires a general geography lookup, not concept
    # evidence from an unrelated canonical entity mentioned in the same query.
    r"\bcapital\s+of\b",
)

_CONCEPT_PATTERNS = (
    r"^what is\b",
    r"^define\b",
    r"\bmeaning of\b",
    r"\bconcept of\b",
    r"\bdifference between\b",
)

_EXPLANATION_PATTERNS = (
    r"^how\b",
    r"^why\b",
    r"\bexplain\b",
    r"\bwalk me through\b",
)


def classify_query(query: str) -> QueryType:
    text = query.strip().lower()
    if not text:
        return QueryType.KNOWLEDGE_QUERY

    if any(re.search(pattern, text) for pattern in _WEB_LOOKUP_PATTERNS):
        return QueryType.WEB_LOOKUP
    if any(re.search(pattern, text) for pattern in _EXPLANATION_PATTERNS):
        return QueryType.EXPLANATION_QUERY
    if any(re.search(pattern, text) for pattern in _CONCEPT_PATTERNS):
        return QueryType.CONCEPT_QUERY
    return QueryType.KNOWLEDGE_QUERY
