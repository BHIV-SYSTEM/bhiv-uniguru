from __future__ import annotations
from collections import OrderedDict
import logging
import threading

import hashlib
import os
import re
import threading
import time
import uuid
import requests
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from service.live_service import LiveUniGuruService
from service.query_classifier import QueryType, classify_query


class QueryRoutingType(str, Enum):
    KNOWLEDGE_QUERY = "KNOWLEDGE_QUERY"
    SYSTEM_QUERY = "SYSTEM_QUERY"
    WORKFLOW_QUERY = "WORKFLOW_QUERY"
    TOOL_QUERY = "TOOL_QUERY"
    CODE_QUERY = "CODE_QUERY"
    DIRECT_QUERY = "DIRECT_QUERY"
    GENERAL_LLM_QUERY = "GENERAL_LLM_QUERY"


class RouteTarget(str, Enum):
    ROUTE_UNIGURU = "ROUTE_UNIGURU"
    ROUTE_LLM = "ROUTE_LLM"
    ROUTE_WORKFLOW = "ROUTE_WORKFLOW"
    ROUTE_SYSTEM = "ROUTE_SYSTEM"


_SYSTEM_PATTERNS = (
    r"\bsudo\b",
    r"\brm\s+-",
    r"\bdel\s+",
    r"\bformat\s+",
    r"\bshutdown\b",
    r"\brestart\b",
    r"\bsystemctl\b",
    r"\bpowershell\b",
    r"\bcmd\.exe\b",
)

_WORKFLOW_PATTERNS = (
    r"\bcreate\b.*\b(ticket|task|workflow|incident|approval)\b",
    r"\bupdate\b.*\b(ticket|task|workflow|incident|approval)\b",
    r"\bapprove\b.*\b(request|workflow|task|ticket)\b",
    r"\bschedule\b.*\b(call|meeting|job|workflow|task)\b",
    r"\bstart\b.*\bworkflow\b",
    r"\btrigger\b.*\bworkflow\b",
)

_TOOL_PATTERNS = (
    r"\buse\b.*\btool\b",
    r"\binvoke\b.*\bapi\b",
    r"\bexecute\b.*\bscript\b",
    r"\brun\b.*\b(sql|query|tool)\b",
)

_KNOWLEDGE_PATTERNS = (
    r"^(what|who|when|where|why|how)\b",
    r"\bexplain\b",
    r"\bdefine\b",
    r"\btell me about\b",
    r"\bdifference between\b",
)

_GENERAL_CHAT_PATTERNS = (
    r"^(hi|hello|hey)\b",
    r"\bhow are you\b",
    r"\bwhat's up\b",
    r"\bhow is it going\b",
)

_CREATIVE_PATTERNS = (
    r"\b(poem|poetry|haiku|shayari)\b",
    r"\b(joke|funny)\b",
    r"\b(rap|lyrics|song)\b",
    r"\b(story|short story)\b",
    r"\b(motivational)\b",
    r"\b(write|compose|create)\b.*\b(poem|joke|rap|story|lyrics)\b",
)

_LOGGER = logging.getLogger(__name__)

_DIRECT_LLM_PATTERNS = (
    r"\b(?:write|show|give|create)\b.*\b(?:code|function|program|script)\b",
    r"\b(?:python|javascript|typescript|java|c\+\+|fastapi)\b.*\b(?:code|function|program|script|work)\b",
    r"\b(?:explain|define)\s+recursion\b",
    r"^(?:(?:what is|solve|calculate)\s+)?-?\d+(?:\.\d+)?\s*[+\-*/]\s*-?\d+(?:\.\d+)?\??$",
    # General "what is X" questions that don't need KB retrieval
    r"^what\s+is\s+\w+",
    r"^what\s+are\s+\w+",
    r"^(?:explain|describe|tell me about)\s+\w+",
    r"\b(?:python|javascript|java|machine learning|ai|artificial intelligence|nlp|deep learning|fastapi|django|flask|react|nodejs)\b",
)

_CODE_REQUEST_PATTERNS = (
    r"\b(?:write|show|give|create|make|implement|generate)\b.{0,120}\b(?:code|function|program|script|algorithm)\b",
    r"\b(?:code|function|program|script|algorithm)\b.{0,100}\b(?:in|using|with)\s+(?:python|javascript|typescript|java|c\+\+|cpp|c#|go|golang|rust)\b",
    r"\b(?:debug|fix|review|explain)\b.{0,100}\bcode\b",
)

_STRICT_EVIDENCE_PATTERNS = (
    r"\baccording to\b",
    r"\b(?:provided|uploaded|attached)\s+(?:source|document|file|text|passage)\b",
    r"\b(?:the|this|that)\s+(?:source|document|file|text|passage)\b",
    r"\b(?:cite|citation|source[- ]backed|verify|verified|verification)\b",
    r"\bmentioned in\b",
    r"\bfrom\s+(?:the\s+)?(?:document|source|text|passage|file)\b",
    r"\b(?:balbharati|ncert|textbook|curriculum)\b",
)


@dataclass(frozen=True)
class RoutingDecision:
    query_type: QueryRoutingType
    route: RouteTarget


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class _LatencyCircuitBreaker:
    def __init__(self, threshold_ms: float, open_seconds: float) -> None:
        self.threshold_ms = threshold_ms
        self.open_seconds = open_seconds
        self._open_until = 0.0
        self._lock = threading.Lock()

    def should_fallback(self) -> bool:
        now = time.monotonic()
        with self._lock:
            return now < self._open_until

    def record_latency(self, latency_ms: float) -> None:
        if latency_ms <= self.threshold_ms:
            return
        with self._lock:
            self._open_until = max(self._open_until, time.monotonic() + self.open_seconds)


class ConversationRouter:
    def __init__(
        self,
        uniguru_service: Optional[LiveUniGuruService] = None,
        latency_threshold_ms: Optional[float] = None,
        breaker_open_seconds: Optional[float] = None,
        allow_unverified_fallback: Optional[bool] = None,
    ) -> None:
        self._service = uniguru_service or LiveUniGuruService()
        threshold = latency_threshold_ms or float(os.getenv("UNIGURU_ROUTER_LATENCY_THRESHOLD_MS", "1200"))
        open_seconds = breaker_open_seconds or float(os.getenv("UNIGURU_ROUTER_CIRCUIT_OPEN_SECONDS", "30"))
        if allow_unverified_fallback is None:
            allow_unverified_fallback = (
                os.getenv("UNIGURU_ROUTER_UNVERIFIED_FALLBACK", "true").strip().lower() in {"1", "true", "yes", "on"}
            )
        self._allow_unverified_fallback = bool(allow_unverified_fallback)
        self._breaker = _LatencyCircuitBreaker(threshold_ms=threshold, open_seconds=open_seconds)
        # No implicit demo provider: missing configuration is reported as unavailable.
        self._llm_url = os.getenv("UNIGURU_LLM_URL", "").strip()
        self._llm_model = os.getenv("UNIGURU_LLM_MODEL", "").strip()
        self._llm_fallback_url = os.getenv("UNIGURU_LLM_FALLBACK_URL", "").strip()
        self._llm_fallback_model = os.getenv("UNIGURU_LLM_FALLBACK_MODEL", "").strip()
        self._llm_fallback_api_key = os.getenv("UNIGURU_LLM_FALLBACK_API_KEY", "").strip()
        try:
            configured_timeout = float(os.getenv("UNIGURU_LLM_TIMEOUT_SECONDS", "20"))
        except ValueError:
            _LOGGER.warning("Invalid LLM timeout setting; using the 20-second default.")
            configured_timeout = 20.0
        self._llm_timeout = min(max(configured_timeout, 1.0), 60.0)
        self._llm_api_key = os.getenv("UNIGURU_LLM_API_KEY", "").strip()
        try:
            configured_retries = int(os.getenv("UNIGURU_LLM_MAX_RETRIES", "1"))
        except ValueError:
            _LOGGER.warning("Invalid LLM retry setting; using one bounded retry.")
            configured_retries = 1
        self._llm_max_retries = min(max(configured_retries, 0), 1)
        self._llm_available: Optional[bool] = None
        self._session_memory: OrderedDict[tuple[str, str], Dict[str, Any]] = OrderedDict()
        self._session_memory_lock = threading.Lock()

    @staticmethod
    def _session_key(context: Dict[str, Any]) -> Optional[tuple[str, str]]:
        session_id = str(context.get("session_id") or "").strip()
        if not session_id:
            return None
        user_scope = str(context.get("user_id") or context.get("caller") or "anonymous")
        if user_scope.strip().casefold() in {"anonymous", "anonymous-client"}:
            return None
        return user_scope, session_id

    def _get_session_memory(self, context: Dict[str, Any]) -> Dict[str, Any]:
        key = self._session_key(context)
        if key is None:
            return {}
        with self._session_memory_lock:
            state = self._session_memory.get(key, {}).copy()
            if key in self._session_memory:
                self._session_memory.move_to_end(key)
            return state

    def _save_session_memory(self, context: Dict[str, Any], state: Dict[str, Any]) -> None:
        key = self._session_key(context)
        if key is None:
            return
        with self._session_memory_lock:
            self._session_memory[key] = state.copy()
            self._session_memory.move_to_end(key)
            while len(self._session_memory) > 1024:
                self._session_memory.popitem(last=False)

    @staticmethod
    def _conversation_answer(query: str, state: Dict[str, str]) -> Optional[str]:
        text = query.strip()
        lower = text.casefold().strip(" .,!?")
        introduction = re.fullmatch(r"my name is\s+([A-Za-z][A-Za-z' -]{0,59})", lower)
        if introduction:
            name = text.strip().rstrip(".!?")[len("my name is"):].strip()
            state["preferred_name"] = name
            return f"Hi {name}! Nice to meet you. How can I help you?"
        if re.fullmatch(r"(?:hi|hello|hey|good morning|good afternoon|good evening)(?: there)?", lower):
            name = state.get("preferred_name")
            return f"Hello {name}! How can I help you today?" if name else "Hello! How can I help you today?"
        if re.fullmatch(r"(?:goodbye|bye|see you|see you later)", lower):
            name = state.get("preferred_name")
            return f"Goodbye, {name}. Take care!" if name else "Goodbye! Take care."
        if re.fullmatch(r"(?:how are you|how are you doing|how's it going)", lower):
            return "I'm doing great! Thanks for asking. How can I help you?"
        if re.search(r"\bwhat is your name\b|\bwhat's your name\b|\bwho are you\b", lower):
            return "My name is UniGuru. How can I help you?"
        if re.search(r"\bcan you help me with my question\b|\bcan you help me\b", lower):
            name = state.get("preferred_name")
            return f"Of course, {name}. What would you like help with?" if name else "Of course. What would you like help with?"
        return None

    @staticmethod
    def _requires_strict_verification(query: str) -> bool:
        return any(re.search(pattern, query.casefold()) for pattern in _STRICT_EVIDENCE_PATTERNS)

    @staticmethod
    def _log_route(
        *,
        query: str,
        intent: str,
        route: str,
        retrieval: str,
        chunks: int,
        verification: str,
        source_type: str,
        selected_sources: Optional[list[Dict[str, Any]]] = None,
        fallback: str = "none",
    ) -> None:
        _LOGGER.debug(
            "[UniGuru Router] query_hash=%s intent=%s route=%s retrieval=%s retrieved_chunks=%d "
            "verification=%s source_type=%s selected_sources=%s fallback=%s",
            hashlib.sha256(query.encode("utf-8")).hexdigest()[:12],
            intent,
            route,
            retrieval,
            chunks,
            verification,
            source_type,
            selected_sources or [],
            fallback,
        )

    @staticmethod
    def _requests_absent_kb_information(query: str) -> bool:
        return bool(re.search(
            r"\bnot\s+(?:present\s+)?in\s+(?:the\s+)?(?:kb|knowledge\s+base)\b",
            query.casefold(),
        ))

    @staticmethod
    def _attach_processing_diagnostics(
        response: Dict[str, Any],
        query_type: QueryRoutingType,
        route: RouteTarget,
        *,
        interpretation_status: str = "success",
    ) -> None:
        retrieval_trace = response.get("retrieval_trace")
        evidence_sources = (
            retrieval_trace.get("evidence_sources", [])
            if isinstance(retrieval_trace, dict)
            else []
        )
        citations = response.get("citations")
        retrieved_evidence = response.get("retrieved_evidence")
        retrieval_status = response.get("retrieval_status")
        if retrieval_status not in {"success", "empty", "skipped", "failed"}:
            if not response.get("retrieval_performed"):
                retrieval_status = "skipped"
            elif evidence_sources or citations or retrieved_evidence is True:
                retrieval_status = "success"
            else:
                retrieval_status = "empty"

        provider_status = str(response.get("provider_status") or "")
        if provider_status == "success":
            generation_status = "success"
        elif provider_status == "unconfigured":
            generation_status = "unavailable"
        elif provider_status in {"failed", "invalid_response"}:
            generation_status = provider_status
        elif response.get("source_type") == "conversation":
            generation_status = "not_run"
        elif route == RouteTarget.ROUTE_LLM:
            generation_status = "unavailable"
        elif response.get("decision") == "answer":
            generation_status = "success"
        else:
            generation_status = "not_run"

        selected_sources = []
        if isinstance(evidence_sources, list):
            for evidence in evidence_sources[:10]:
                if not isinstance(evidence, dict):
                    continue
                source = str(
                    evidence.get("path") or evidence.get("file") or evidence.get("source") or ""
                ).strip()
                if not source:
                    continue
                raw_score = (
                    evidence.get("reranker_score")
                    or evidence.get("score")
                    or evidence.get("retrieval_score")
                    or evidence.get("evidence_coverage")
                )
                try:
                    score = round(float(raw_score), 4) if raw_score is not None else None
                except (TypeError, ValueError):
                    score = None
                selected_sources.append({"source": source, "score": score})

        matched_signals = response.get("matched_signals")
        rejected_signals = response.get("rejected_signals")
        signals_evaluated = isinstance(matched_signals, list) or isinstance(rejected_signals, list)
        if retrieval_status == "success":
            evidence_count = len(evidence_sources) if isinstance(evidence_sources, list) else 0
            if not evidence_count and isinstance(citations, list):
                evidence_count = len(citations)
            if not evidence_count and retrieved_evidence is True:
                evidence_count = 1
        else:
            evidence_count = 0

        response["processing_diagnostics"] = {
            "interpretation": {
                "status": interpretation_status,
                "intent": query_type.value,
                "route": route.value,
            },
            "retrieval": {
                "status": retrieval_status,
                "evidence_count": evidence_count,
                "selected_sources": selected_sources,
            },
            "generation": {
                "status": generation_status,
                "provider_status": provider_status or None,
            },
            "confidence": {
                "answer_quality": {"status": "not_scored", "value": None},
                "retrieval": {
                    "status": "not_scored" if retrieval_status == "success" else "not_applicable",
                    "value": None,
                },
            },
            "signals": {
                "status": "evaluated" if signals_evaluated else "not_evaluated",
                "accepted": len(matched_signals) if isinstance(matched_signals, list) else None,
                "rejected": len(rejected_signals) if isinstance(rejected_signals, list) else None,
            },
        }

    @staticmethod
    def _followup_query(query: str, state: Dict[str, str]) -> Optional[str]:
        lower = query.casefold()
        is_followup = bool(
            re.match(r"^(?:explain|simplify|describe|summarize|elaborate on)\s+(?:it|that|this|those|them)\b", lower)
            or re.match(r"^(?:what|how) about\s+(?:it|that|this|those|them)\b", lower)
            or re.match(r"^(?:tell me more|go into more detail|give me an example)\b", lower)
        )
        if not is_followup:
            return None
        previous_query = state.get("last_query")
        if not previous_query:
            return ""
        return f"{previous_query} {query}"

    def llm_status(self) -> Dict[str, Any]:
        primary_configured = bool(self._llm_url) and not self._llm_url.startswith("internal://")
        fallback_configured = bool(self._llm_fallback_url) and not self._llm_fallback_url.startswith("internal://")
        configured = primary_configured or fallback_configured
        internal_demo = self._llm_url.startswith("internal://") and not fallback_configured
        return {
            "configured": configured,
            "endpoint": self._llm_url or self._llm_fallback_url or None,
            "model": self._llm_model or self._llm_fallback_model or None,
            "internal_demo_mode": internal_demo,
            "available": configured and self._llm_available is True,
            "last_request_succeeded": self._llm_available,
        }

    def route_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        started = time.perf_counter()
        context_map = dict(context or {})
        session_state = self._get_session_memory(context_map)
        conversational_answer = self._conversation_answer(query, session_state)
        if conversational_answer is not None:
            self._save_session_memory(context_map, session_state)
            response = self._build_router_contract_response(
                decision="answer",
                answer=conversational_answer,
                reason="Handled as conversational intent without knowledge retrieval.",
                query_type=QueryRoutingType.GENERAL_LLM_QUERY,
                route=RouteTarget.ROUTE_LLM,
                verification_status="NOT_REQUIRED",
                session_id=context_map.get("session_id"),
                governance_allowed=True,
                governance_reason="Conversational response; no knowledge-base evidence required.",
            )
            response.update(
                source_type="conversation",
                verified=False,
                retrieved_evidence=False,
            )
            response.pop("_resolved_route", None)
            response["routing"] = {
                "query_type": QueryRoutingType.GENERAL_LLM_QUERY.value,
                "route": RouteTarget.ROUTE_LLM.value,
                "router_latency_ms": round((time.perf_counter() - started) * 1000, 3),
            }
            self._attach_processing_diagnostics(
                response, QueryRoutingType.GENERAL_LLM_QUERY, RouteTarget.ROUTE_LLM
            )
            self._log_route(
                query=query,
                intent="greeting_or_conversation",
                route=RouteTarget.ROUTE_LLM.value,
                retrieval="skipped",
                chunks=0,
                verification="skipped",
                source_type="conversation",
            )
            self._remember_turn(session_state, query, conversational_answer)
            self._save_session_memory(context_map, session_state)
            return response

        if self._requests_absent_kb_information(query):
            response = self._build_router_contract_response(
                decision="answer",
                answer="I couldn't find sufficient information in the available documents.",
                reason="The request explicitly states that the requested information is outside the knowledge base.",
                query_type=QueryRoutingType.KNOWLEDGE_QUERY,
                route=RouteTarget.ROUTE_UNIGURU,
                verification_status="UNVERIFIED",
                session_id=context_map.get("session_id"),
                governance_allowed=False,
                governance_reason="No verified knowledge evidence was available.",
            )
            response.pop("_resolved_route", None)
            response["routing"] = {
                "query_type": QueryRoutingType.KNOWLEDGE_QUERY.value,
                "route": RouteTarget.ROUTE_UNIGURU.value,
                "router_latency_ms": round((time.perf_counter() - started) * 1000, 3),
            }
            response.update(source_type="rag", verified=False, retrieved_evidence=False)
            self._attach_processing_diagnostics(
                response, QueryRoutingType.KNOWLEDGE_QUERY, RouteTarget.ROUTE_UNIGURU
            )
            self._log_route(
                query=query,
                intent="explicitly_absent_from_knowledge_base",
                route=RouteTarget.ROUTE_UNIGURU.value,
                retrieval="skipped",
                chunks=0,
                verification="performed",
                source_type="rag",
            )
            return response

        original_query = query
        followup_query = self._followup_query(original_query, session_state)
        if followup_query == "":
            response = self._build_router_contract_response(
                decision="answer",
                answer="What would you like me to explain?",
                reason="A follow-up was received without a prior topic in this session.",
                query_type=QueryRoutingType.GENERAL_LLM_QUERY,
                route=RouteTarget.ROUTE_LLM,
                verification_status="UNVERIFIED",
                session_id=context_map.get("session_id"),
                governance_allowed=True,
                governance_reason="Clarification requested before retrieval.",
            )
            response.pop("_resolved_route", None)
            response["routing"] = {
                "query_type": QueryRoutingType.GENERAL_LLM_QUERY.value,
                "route": RouteTarget.ROUTE_LLM.value,
                "router_latency_ms": round((time.perf_counter() - started) * 1000, 3),
            }
            response.update(source_type="conversation", verified=False, retrieved_evidence=False)
            self._attach_processing_diagnostics(
                response,
                QueryRoutingType.GENERAL_LLM_QUERY,
                RouteTarget.ROUTE_LLM,
                interpretation_status="clarification_required",
            )
            self._log_route(
                query=query,
                intent="followup_needs_clarification",
                route=RouteTarget.ROUTE_LLM.value,
                retrieval="skipped",
                chunks=0,
                verification="skipped",
                source_type="conversation",
            )
            return response
        effective_query = followup_query or original_query

        query_type = self.classify(query=effective_query, context=context_map)
        target = self.select_route(query_type=query_type)
        session_id = context_map.get("session_id")

        history = self._history_for_query(context_map, session_state, original_query)
        # Conversation text is used only for generation, not forwarded into retrieval/orchestration.
        context_map.pop("conversation_history", None)
        if target == RouteTarget.ROUTE_SYSTEM:
            response = self._build_system_block_response(query_type=query_type, session_id=session_id)
        elif target == RouteTarget.ROUTE_WORKFLOW:
            response = self._build_workflow_response(query=query, query_type=query_type, session_id=session_id)
        elif target == RouteTarget.ROUTE_LLM:
            response = self._build_llm_response(
                query=original_query,
                query_type=query_type,
                session_id=session_id,
                warning=None,
                history=history,
            )
        else:
            response = self._dispatch_to_uniguru(
                query=effective_query, context=context_map, query_type=query_type, history=history
            )

        resolved_route = str(response.pop("_resolved_route", target.value))
        routing_latency = (time.perf_counter() - started) * 1000
        response["routing"] = {
            "query_type": query_type.value,
            "route": resolved_route,
            "router_latency_ms": round(routing_latency, 3),
        }
        self._attach_processing_diagnostics(response, query_type, RouteTarget(resolved_route))
        if query_type in {
            QueryRoutingType.KNOWLEDGE_QUERY,
            QueryRoutingType.DIRECT_QUERY,
            QueryRoutingType.CODE_QUERY,
        }:
            session_state["last_query"] = session_state.get("last_query") if followup_query else original_query
            self._save_session_memory(context_map, session_state)
        retrieval_trace = response.get("retrieval_trace")
        evidence_sources = retrieval_trace.get("evidence_sources", []) if isinstance(retrieval_trace, dict) else []
        diagnostics = response.get("processing_diagnostics", {})
        retrieval_diagnostics = diagnostics.get("retrieval", {}) if isinstance(diagnostics, dict) else {}
        selected_sources = retrieval_diagnostics.get("selected_sources", [])
        if not isinstance(selected_sources, list):
            selected_sources = []
        provider_status = str(response.get("provider_status") or "")
        retrieval_status = str(response.get("retrieval_status") or "skipped")
        if provider_status in {"unconfigured", "failed", "invalid_response"}:
            fallback = f"llm_{provider_status}"
        elif retrieval_status in {"empty", "failed"} and response.get("source_type") in {
            "llm_general_knowledge",
            "llm_code_generation",
        }:
            fallback = f"retrieval_{retrieval_status}_to_llm"
        else:
            fallback = "none"
        self._remember_turn(session_state, original_query, str(response.get("answer") or ""))
        self._save_session_memory(context_map, session_state)
        self._log_route(
            query=original_query,
            intent=query_type.value,
            route=resolved_route,
            retrieval=retrieval_status,
            chunks=len(evidence_sources) if isinstance(evidence_sources, list) else 0,
            verification=str(response.get("verification_status") or "NOT_REQUIRED"),
            source_type=str(response.get("source_type") or "unknown"),
            selected_sources=selected_sources,
            fallback=fallback,
        )
        return response

    def classify(self, query: str, context: Optional[Dict[str, Any]] = None) -> QueryRoutingType:
        text = query.strip().lower()
        if not text:
            return QueryRoutingType.GENERAL_LLM_QUERY

        if any(re.search(pattern, text) for pattern in _SYSTEM_PATTERNS):
            return QueryRoutingType.SYSTEM_QUERY
        if any(re.search(pattern, text) for pattern in _WORKFLOW_PATTERNS):
            return QueryRoutingType.WORKFLOW_QUERY
        if any(re.search(pattern, text) for pattern in _TOOL_PATTERNS):
            return QueryRoutingType.TOOL_QUERY
        if any(re.search(pattern, text) for pattern in _CODE_REQUEST_PATTERNS):
            return QueryRoutingType.CODE_QUERY
        if any(re.search(pattern, text) for pattern in _DIRECT_LLM_PATTERNS[3:4]):
            return QueryRoutingType.GENERAL_LLM_QUERY
        if any(re.search(pattern, text) for pattern in _GENERAL_CHAT_PATTERNS):
            return QueryRoutingType.GENERAL_LLM_QUERY
        if any(re.search(pattern, text) for pattern in _CREATIVE_PATTERNS):
            return QueryRoutingType.GENERAL_LLM_QUERY

        if context and context.get("prefer_verified_rag"):
            return QueryRoutingType.KNOWLEDGE_QUERY

        if self._requires_strict_verification(query):
            return QueryRoutingType.KNOWLEDGE_QUERY

        upstream_type = classify_query(text)
        if upstream_type in {
            QueryType.KNOWLEDGE_QUERY,
            QueryType.CONCEPT_QUERY,
            QueryType.EXPLANATION_QUERY,
        }:
            from router.universal_query_router import get_universal_router

            if get_universal_router().route(query, context=context).get("requires_rag"):
                return QueryRoutingType.KNOWLEDGE_QUERY
            return QueryRoutingType.DIRECT_QUERY
        if upstream_type == QueryType.WEB_LOOKUP:
            return QueryRoutingType.KNOWLEDGE_QUERY
        if any(re.search(pattern, text) for pattern in _DIRECT_LLM_PATTERNS):
            return QueryRoutingType.GENERAL_LLM_QUERY
        return QueryRoutingType.GENERAL_LLM_QUERY

    @staticmethod
    def select_route(query_type: QueryRoutingType) -> RouteTarget:
        if query_type == QueryRoutingType.SYSTEM_QUERY:
            return RouteTarget.ROUTE_SYSTEM
        if query_type in {QueryRoutingType.WORKFLOW_QUERY, QueryRoutingType.TOOL_QUERY}:
            return RouteTarget.ROUTE_WORKFLOW
        if query_type in {
            QueryRoutingType.CODE_QUERY,
            QueryRoutingType.DIRECT_QUERY,
            QueryRoutingType.GENERAL_LLM_QUERY,
        }:
            return RouteTarget.ROUTE_LLM
        return RouteTarget.ROUTE_UNIGURU

    def _dispatch_to_uniguru(
        self,
        query: str,
        context: Dict[str, Any],
        query_type: QueryRoutingType,
        history: Optional[list[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        session_id = context.get("session_id")
        allow_web = bool(context.get("allow_web", False))
        user_id = str(context.get("caller") or context.get("user_id") or "demo-user")

        try:
            if query_type == QueryRoutingType.KNOWLEDGE_QUERY and context.get("prefer_verified_rag"):
                shared_response = self._service.ask(
                    user_query=query,
                    session_id=session_id,
                    context=context,
                    allow_web_retrieval=allow_web,
                )
                shared_trace = shared_response.get("retrieval_trace") or {}
                if (
                    shared_response.get("verification_status")
                    in {"VERIFIED", "VERIFIED_PARTIAL", "PARTIAL"}
                    and shared_trace.get("match_found")
                    and str(shared_response.get("answer") or "").strip()
                ):
                    shared_response.update(
                        source_type="rag",
                        verified=True,
                        retrieved_evidence=bool(shared_trace.get("evidence_sources")),
                        retrieval_performed=True,
                        retrieval_status="success",
                    )
                    return shared_response

            from service.universal_orchestrator import get_universal_orchestrator
            orchestrator = get_universal_orchestrator()
            orch_res = orchestrator.process_query(
                query=query,
                session_id=session_id,
                user_id=user_id,
                context=context,
                allow_web=allow_web,
            )
            verification_status = str(orch_res.get("verification_status") or "UNVERIFIED").upper()
            answer = str(orch_res.get("answer") or "I do not have verified knowledge to answer this question.")
            citations = orch_res.get("citations") or []
            sources_consulted = orch_res.get("sources_consulted") or []
            category = str(orch_res.get("category") or "").upper()
            retrieval_performed = category in {"KNOWLEDGE_BASE", "DOCUMENT_QUESTION"} or any(
                "rag" in str(source).casefold() for source in sources_consulted
            )
            if verification_status == "VERIFIED" and self.llm_status()["configured"]:
                verified_context = answer
                if citations:
                    citation_text = "; ".join(str(citation)[:300] for citation in citations[:8])
                    verified_context += "\nVerified citations: " + citation_text
                generated = self._request_llm(
                    query=query,
                    session_id=session_id,
                    history=history,
                    verified_context=verified_context,
                    verification_status=verification_status,
                )
                if generated.get("provider_status") == "success":
                    answer = generated["answer"]
            if (
                verification_status != "VERIFIED"
                and self._allow_unverified_fallback
                and not self._requires_strict_verification(query)
            ):
                return self._build_llm_response(
                    query=query, query_type=query_type, session_id=session_id,
                    warning="The knowledge base did not provide verified evidence.",
                    history=history, verification_status=verification_status,
                    retrieval_status="empty" if retrieval_performed else "skipped",
                )
            response = self._build_router_contract_response(
                decision="answer" if verification_status == "VERIFIED" else "block",
                answer=answer,
                reason=f"Resolved by {orch_res.get('category')} capability.",
                query_type=query_type,
                route=RouteTarget.ROUTE_UNIGURU,
                verification_status=verification_status,
                session_id=session_id,
                governance_allowed=verification_status == "VERIFIED",
                governance_reason=(f"Capability {orch_res.get('category')} verified." if verification_status == "VERIFIED" else "No verified knowledge evidence was available."),
            )
            if verification_status != "VERIFIED":
                response["answer"] = "I couldn't find sufficient information in the available documents."
            source_type = (
                "rag" if retrieval_performed
                else str(sources_consulted[0]) if sources_consulted
                else "direct_capability"
            )
            has_retrieved_evidence = bool(
                citations or orch_res.get("evidence")
            ) and verification_status == "VERIFIED"
            retrieval_status = (
                "success" if retrieval_performed and has_retrieved_evidence
                else "empty" if retrieval_performed else "skipped"
            )
            response.update(
                source_type=source_type,
                verified=verification_status == "VERIFIED",
                retrieved_evidence=has_retrieved_evidence,
                retrieval_performed=retrieval_performed,
                retrieval_status=retrieval_status,
                citations=citations,
            )
            retrieval_trace = orch_res.get("retrieval_trace")
            if isinstance(retrieval_trace, dict):
                response["retrieval_trace"] = retrieval_trace
            return response
        except Exception as exc:
            _LOGGER.exception("Universal orchestrator dispatch failed (%s).", type(exc).__name__)
            return self._build_llm_response(
                query=query,
                query_type=query_type,
                session_id=session_id,
                warning="The knowledge service failed; no verified result is available.",
                history=history,
                retrieval_status="failed",
            )

    def _build_system_block_response(
        self,
        query_type: QueryRoutingType,
        session_id: Optional[str],
    ) -> Dict[str, Any]:
        return self._build_router_contract_response(
            decision="block",
            answer="System-level command requests are blocked by BHIV routing policy.",
            reason="ROUTE_SYSTEM policy enforced.",
            query_type=query_type,
            route=RouteTarget.ROUTE_SYSTEM,
            verification_status="UNVERIFIED",
            session_id=session_id,
            governance_allowed=False,
            governance_reason="System command blocked by router policy.",
        )

    def _build_workflow_response(
        self,
        query: str,
        query_type: QueryRoutingType,
        session_id: Optional[str],
    ) -> Dict[str, Any]:
        return self._build_router_contract_response(
            decision="answer",
            answer=f"Delegated to workflow engine: {query}",
            reason="ROUTE_WORKFLOW policy applied.",
            query_type=query_type,
            route=RouteTarget.ROUTE_WORKFLOW,
            verification_status="PARTIAL",
            session_id=session_id,
            governance_allowed=True,
            governance_reason="Delegated workflow response.",
        )

    def _build_llm_response(
        self,
        query: str,
        query_type: QueryRoutingType,
        session_id: Optional[str],
        warning: Optional[str],
        history: Optional[list[Dict[str, str]]] = None,
        verified_context: str = "",
        verification_status: str = "NOT_REQUIRED",
        retrieval_status: str = "skipped",
    ) -> Dict[str, Any]:
        llm_result = self._request_llm(
            query=query,
            session_id=session_id,
            history=history,
            verified_context=verified_context,
            verification_status=verification_status,
        )
        answer = llm_result["answer"]
        if warning and llm_result.get("provider_status") == "success":
            answer = f"{warning} {answer}"
        succeeded = llm_result.get("provider_status") == "success"
        response = self._build_router_contract_response(
            decision="answer" if succeeded else "block",
            answer=answer,
            reason=llm_result["reason"],
            query_type=query_type,
            route=RouteTarget.ROUTE_LLM,
            verification_status="NOT_REQUIRED" if succeeded else "UNVERIFIED",
            session_id=session_id,
            governance_allowed=succeeded,
            governance_reason=llm_result["governance_reason"],
        )
        response.update(
            source_type=(
                "llm_code_generation"
                if succeeded and query_type == QueryRoutingType.CODE_QUERY
                else "llm_general_knowledge" if succeeded else "llm_unavailable"
            ),
            verified=False,
            retrieved_evidence=False,
            retrieval_performed=retrieval_status != "skipped",
            retrieval_status=retrieval_status,
            provider_status=llm_result.get("provider_status", "failed"),
        )
        return response

    @staticmethod
    def _bounded_history(history: Any) -> list[Dict[str, str]]:
        if not isinstance(history, list):
            return []
        bounded: list[Dict[str, str]] = []
        for item in history[-12:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            if role is None:
                sender = str(item.get("sender") or "").casefold()
                role = "assistant" if sender in {"bot", "assistant"} else "user" if sender == "user" else None
            if role not in {"user", "assistant"}:
                continue
            content = str(item.get("content") or "").strip()
            if content:
                bounded.append({"role": role, "content": content[:2000]})
        return bounded[-12:]

    def _history_for_query(
        self, context: Dict[str, Any], session_state: Dict[str, Any], current_query: str
    ) -> list[Dict[str, str]]:
        stored = context.get("conversation_history")
        source = stored if isinstance(stored, list) else session_state.get("history", [])
        history = self._bounded_history(source)
        current = " ".join(str(current_query or "").casefold().split())
        # chat_new may include the current user message in its stored transcript;
        # avoid placing that message twice in the model prompt.
        return [
            message for message in history
            if not (message["role"] == "user" and " ".join(message["content"].casefold().split()) == current)
        ][-6:]

    def _remember_turn(self, state: Dict[str, Any], query: str, answer: str) -> None:
        history = self._bounded_history(state.get("history", []))
        if query.strip():
            history.append({"role": "user", "content": query.strip()[:2000]})
        if answer.strip():
            history.append({"role": "assistant", "content": answer.strip()[:2000]})
        state["history"] = history[-6:]

    def _request_llm(
        self,
        query: str,
        session_id: Optional[str],
        history: Optional[list[Dict[str, str]]] = None,
        verified_context: str = "",
        verification_status: str = "NOT_REQUIRED",
    ) -> Dict[str, str]:
        providers = []
        for name, url, model, api_key in (
            ("primary", self._llm_url, self._llm_model, self._llm_api_key),
            ("fallback", self._llm_fallback_url, self._llm_fallback_model, self._llm_fallback_api_key),
        ):
            if not url or url.startswith("internal://"):
                continue
            if any(existing["url"].casefold() == url.casefold() for existing in providers):
                continue
            providers.append({"name": name, "url": url, "model": model, "api_key": api_key})
        if not providers:
            self._llm_available = False
            return {
                "answer": "I can't generate an answer because no language-model provider is configured.",
                "reason": "ROUTE_LLM selected but no language-model provider is configured.",
                "governance_reason": "Generation is unavailable; no fabricated fallback was returned.",
                "provider_status": "unconfigured",
            }

        last_failure = {
            "answer": "I couldn't get a response from the configured language-model provider. Please try again later.",
            "reason": "ROUTE_LLM request to configured provider failed.",
            "governance_reason": "Provider request failed; no canned answer was substituted.",
            "provider_status": "failed",
        }
        for provider in providers:
            result = self._request_llm_provider(
                query=query,
                session_id=session_id,
                history=history,
                verified_context=verified_context,
                verification_status=verification_status,
                provider_url=provider["url"],
                provider_model=provider["model"],
                provider_api_key=provider["api_key"],
                provider_name=provider["name"],
            )
            if result.get("provider_status") == "success":
                return result
            last_failure = result

        self._llm_available = False
        return last_failure

    def _post_llm_with_retries(
        self,
        provider_url: str,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        provider_name: str,
    ) -> Dict[str, Any]:
        for attempt in range(self._llm_max_retries + 1):
            response = None
            try:
                response = requests.post(
                    provider_url,
                    json=payload,
                    headers=headers,
                    timeout=self._llm_timeout,
                )
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    raise ValueError("LLM provider response was not a JSON object.")
                return data
            except Exception as exc:
                status_code = getattr(response, "status_code", None)
                if status_code is None:
                    status_code = getattr(getattr(exc, "response", None), "status_code", None)
                retryable = (
                    isinstance(exc, (requests.Timeout, requests.ConnectionError))
                    or status_code == 429
                    or (isinstance(status_code, int) and status_code >= 500)
                )
                if not retryable or attempt >= self._llm_max_retries:
                    raise
                _LOGGER.warning(
                    "Transient LLM provider failure (%s; status=%s; provider=%s; attempt=%s); retrying.",
                    type(exc).__name__,
                    status_code,
                    provider_name,
                    attempt + 1,
                )
                time.sleep(min(0.25 * (2 ** attempt), 1.0))
        raise RuntimeError("LLM retry loop exited without a response.")

    def _request_llm_provider(
        self,
        query: str,
        session_id: Optional[str],
        history: Optional[list[Dict[str, str]]],
        verified_context: str,
        verification_status: str,
        provider_url: str,
        provider_model: str,
        provider_api_key: str,
        provider_name: str,
    ) -> Dict[str, str]:
        evidence = str(verified_context or "").strip()[:6000]
        if verification_status != "VERIFIED":
            evidence = ""
        code_generation = any(
            re.search(pattern, query.casefold()) for pattern in _CODE_REQUEST_PATTERNS
        )
        system_prompt = (
            "You are UniGuru, a helpful conversational AI assistant. Answer the user's actual question directly. "
            "Use only the verified knowledge context below for claims about UniGuru's knowledge base; do not invent "
            "citations or claim that unsupported material is verified. If that context is empty or insufficient, "
            "say you cannot verify the requested information. General conversation may be answered normally."
        )
        if code_generation:
            system_prompt += (
                " This is a programming solution request: answer the requested task, not with a general "
                "description of the programming language. Include a short introduction, a syntactically valid "
                "fenced code block labeled with the requested language, a brief explanation, and sample output "
                "when appropriate. Preserve the requested language and do not claim the code was executed."
            )
        if evidence:
            system_prompt += "\n\nVERIFIED RETRIEVED CONTEXT (use as evidence; do not add unsupported facts):\n" + evidence
        elif verification_status.upper() == "UNVERIFIED":
            system_prompt += "\n\nRETRIEVAL STATUS: No verified knowledge-base evidence was found. Do not present a knowledge-base claim as verified; clearly abstain when evidence is required."
        bounded_history = self._bounded_history(history or [])[-6:]
        messages = [{"role": "system", "content": system_prompt}, *bounded_history, {"role": "user", "content": query}]

        llm_url_lower = provider_url.lower()
        is_openai_chat_style = "/openai/v1/chat/completions" in llm_url_lower or llm_url_lower.endswith("/chat/completions")
        if is_openai_chat_style:
            sanitized_payload = {"model": provider_model, "messages": messages, "stream": False}
        else:
            rendered_prompt = "\n\n".join(
                f"{message['role'].capitalize()}:\n{message['content']}" for message in messages
            ) + "\n\nAssistant:"
            sanitized_payload = {
                "model": provider_model or None,
                "messages": messages,
                "system": system_prompt,
                "prompt": rendered_prompt,
                "query": query,
                "input": query,
                "session_id": session_id,
                "stream": False,
            }
            sanitized_payload = {key: value for key, value in sanitized_payload.items() if value is not None}
        headers = {"Content-Type": "application/json"}
        if self._llm_api_key:
            headers["Authorization"] = f"Bearer {self._llm_api_key}"

        headers.pop("Authorization", None)
        if provider_api_key:
            headers["Authorization"] = "Bearer " + provider_api_key

        retry_messages = messages
        for attempt in range(2 if code_generation else 1):
            payload = dict(sanitized_payload)
            payload["messages"] = retry_messages
            if not is_openai_chat_style:
                payload["prompt"] = "\n\n".join(
                    f"{message['role'].capitalize()}:\n{message['content']}"
                    for message in retry_messages
                ) + "\n\nAssistant:"
            try:
                data = self._post_llm_with_retries(
                    provider_url=provider_url,
                    payload=payload,
                    headers=headers,
                    provider_name=provider_name,
                )
            except Exception as exc:
                _LOGGER.warning(
                    "LLM provider request failed (%s; provider=%s).",
                    type(exc).__name__,
                    provider_name,
                )
                return {
                    "answer": "I couldn't get a response from the configured language-model provider. Please try again later.",
                    "reason": "ROUTE_LLM request to configured provider failed.",
                    "governance_reason": "Provider request failed; no canned answer was substituted.",
                    "provider_status": "failed",
                }

            answer = str(
                data.get("answer") or data.get("response") or data.get("output") or data.get("content") or ""
            ).strip()
            message_data = data.get("message")
            if not answer and isinstance(message_data, dict):
                answer = str(message_data.get("content") or "").strip()
            choices = data.get("choices")
            if not answer and isinstance(choices, list) and choices and isinstance(choices[0], dict):
                choice = choices[0]
                choice_message = choice.get("message")
                if isinstance(choice_message, dict):
                    answer = str(choice_message.get("content") or "").strip()
                if not answer:
                    answer = str(choice.get("text") or "").strip()
            if not answer:
                self._llm_available = False
                return {
                    "answer": "The configured language-model provider returned an empty response. Please try again later.",
                    "reason": "ROUTE_LLM provider returned no answer.",
                    "governance_reason": "Empty provider output was not replaced with a canned answer.",
                    "provider_status": "failed",
                }

            if code_generation and not re.search(r"```[^\n`]*\n[\s\S]+?\n```", answer):
                if attempt == 0:
                    retry_messages = [
                        *messages,
                        {"role": "assistant", "content": answer[:4000]},
                        {
                            "role": "user",
                            "content": "Your previous response did not include a fenced code block. Answer the original programming request with the requested language, executable code in a fenced block, a brief explanation, and sample output when appropriate.",
                        },
                    ]
                    continue
                self._llm_available = False
                _LOGGER.warning("LLM response rejected because a programming request contained no fenced code.")
                return {
                    "answer": "The language-model provider did not return the requested code format. Please try again.",
                    "reason": "ROUTE_LLM provider response did not satisfy the programming response contract.",
                    "governance_reason": "A non-code response was rejected instead of being presented as a solution.",
                    "provider_status": "invalid_response",
                }

            self._llm_available = True
            return {
                "answer": answer,
                "reason": "ROUTE_LLM policy applied via configured language-model provider.",
                "governance_reason": "Delegated open-chat response through configured provider.",
                "provider_status": "success",
            }
        raise RuntimeError("LLM request loop exited without a result.")

    def _build_router_contract_response(
        self,
        decision: str,
        answer: str,
        reason: str,
        query_type: QueryRoutingType,
        route: RouteTarget,
        verification_status: str,
        session_id: Optional[str],
        governance_allowed: bool,
        governance_reason: str,
    ) -> Dict[str, Any]:
        request_id = str(uuid.uuid4())
        signature_payload = f"{decision}|{answer}|{route.value}|{request_id}"
        signature = hashlib.sha256(signature_payload.encode("utf-8")).hexdigest()
        return {
            "decision": decision,
            "answer": answer,
            "session_id": session_id,
            "reason": reason,
            "_resolved_route": route.value,
            "ontology_reference": {
                "concept_id": f"router::{query_type.value.lower()}",
                "domain": "routing",
                "snapshot_version": 0,
                "snapshot_hash": "router-delegated",
                "truth_level": 0,
            },
            "reasoning_trace": {
                "sources_consulted": ["conversation_router"],
                "retrieval_confidence": 0.0,
                "ontology_domain": "routing",
                "verification_status": verification_status,
                "verification_details": f"Delegated via {route.value}",
            },
            "governance_flags": {"safety": not governance_allowed},
            "governance_output": {
                "allowed": governance_allowed,
                "reason": governance_reason,
                "flags": {"router_route": route.value},
            },
            "verification_status": verification_status,
            "status_action": "ALLOW_WITH_DISCLAIMER" if governance_allowed else "REFUSE",
            "enforcement_signature": signature,
            "request_id": request_id,
            "sealed_at": _utc_now_iso(),
            "latency_ms": 0.0,
        }


_DEFAULT_ROUTER = ConversationRouter()


def route_query(query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return _DEFAULT_ROUTER.route_query(query=query, context=context)
