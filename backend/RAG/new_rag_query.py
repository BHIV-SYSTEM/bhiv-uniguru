"""
UniGuru Production RAG Engine Integration Adapter
=================================================
Connects legacy and external RAG entry points to the unified
hybrid retrieval and grounded intelligence engine.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from retrieval.unified_rag_engine import get_unified_engine

_engine_instance = None


class NewRAGEngine:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.unified_engine = get_unified_engine()

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        result = self.unified_engine.retrieve(query, top_k=top_k)
        evidence = result.get("top_evidence", [])
        output = []
        for ev in evidence:
            output.append({
                "text": ev["text"],
                "metadata": {
                    "file_name": ev.get("file_name"),
                    "page_number": ev.get("page", 1),
                    "grade": ev.get("grade"),
                    "subject": ev.get("subject"),
                    "chapter": ev.get("chapter"),
                    "domain": ev.get("domain"),
                },
                "score": float(ev.get("composite_score", ev.get("dense_similarity", 0.0))),
            })
        return output

    def answer_question(self, query: str, max_context_chars: int = 4000, top_k: int = 5) -> Dict[str, Any]:
        result = self.unified_engine.answer_query(query=query, top_k=top_k)
        retrieved = []
        for ev in result.get("evidence", []):
            retrieved.append({
                "text": ev["text"],
                "metadata": {
                    "file_name": ev.get("file_name"),
                    "page_number": ev.get("page", 1),
                },
                "score": float(ev.get("composite_score", 0.0)),
            })
        return {
            "answer": result.get("answer", "No relevant context found."),
            "retrieved": retrieved,
            "verification_status": result.get("verification_status", "UNVERIFIED"),
            "citations": result.get("citations", []),
        }


def get_engine() -> NewRAGEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = NewRAGEngine()
    return _engine_instance
