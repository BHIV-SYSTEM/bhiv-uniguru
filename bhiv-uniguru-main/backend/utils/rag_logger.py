"""Production-grade structured logging for the RAG / retrieval pipeline."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("uniguru.rag")


def _safe(value: Any, max_len: int = 2000) -> Any:
    if isinstance(value, str) and len(value) > max_len:
        return value[:max_len] + "...[truncated]"
    return value


def log_rag_event(stage: str, payload: Dict[str, Any]) -> None:
    record = {"stage": stage, **_safe_dict(payload)}
    logger.info(json.dumps(record, default=str, sort_keys=True))


def _safe_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    return {key: _safe(val) for key, val in data.items()}


def log_incoming_request(query: str, session_id: Optional[str] = None, caller: Optional[str] = None) -> None:
    log_rag_event(
        "incoming_request",
        {"query": query, "session_id": session_id, "caller": caller},
    )


def log_retrieval_result(
    query: str,
    *,
    method: str,
    match_found: bool,
    confidence: float,
    source: Optional[str],
    similarity_scores: Optional[list] = None,
    document_count: int = 0,
) -> None:
    log_rag_event(
        "retrieval_result",
        {
            "query": query,
            "method": method,
            "match_found": match_found,
            "confidence": confidence,
            "source": source,
            "similarity_scores": similarity_scores or [],
            "document_count": document_count,
        },
    )


def log_context_built(query: str, context_chars: int, chunk_count: int) -> None:
    log_rag_event(
        "context_built",
        {"query": query, "context_chars": context_chars, "chunk_count": chunk_count},
    )


def log_prompt(query: str, prompt_preview: str, system_preview: str = "") -> None:
    log_rag_event(
        "prompt_built",
        {
            "query": query,
            "system_preview": system_preview[:500],
            "prompt_preview": prompt_preview[:1500],
        },
    )


def log_model_response(query: str, raw_response: str, parsed_answer: str) -> None:
    log_rag_event(
        "model_response",
        {
            "query": query,
            "raw_response": raw_response[:2000],
            "parsed_answer": parsed_answer[:2000],
        },
    )


def log_final_answer(
    query: str,
    answer: str,
    verification_status: str,
    confidence: float,
    source: str,
) -> None:
    log_rag_event(
        "final_answer",
        {
            "query": query,
            "answer": answer,
            "verification_status": verification_status,
            "confidence": confidence,
            "source": source,
        },
    )


def log_rag_error(stage: str, query: str, error: str) -> None:
    log_rag_event("error", {"stage": stage, "query": query, "error": error})
