from __future__ import annotations
from collections import OrderedDict
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

SAFE_FALLBACK_PREFIX = "I am still learning this topic, but here is a basic explanation..."


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
        # Always default to internal demo mode so ROUTE_LLM remains available
        # even when env files are missing in demo/smoke runs.
        self._llm_url = os.getenv("UNIGURU_LLM_URL", "internal://demo-llm").strip()
        self._llm_model = os.getenv("UNIGURU_LLM_MODEL", "demo-safety-llm").strip()
        self._llm_timeout = float(os.getenv("UNIGURU_LLM_TIMEOUT_SECONDS", "20"))
        self._llm_api_key = os.getenv("UNIGURU_LLM_API_KEY", "").strip()
        self._session_memory: OrderedDict[tuple[str, str], Dict[str, str]] = OrderedDict()
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

    def _get_session_memory(self, context: Dict[str, Any]) -> Dict[str, str]:
        key = self._session_key(context)
        if key is None:
            return {}
        with self._session_memory_lock:
            state = self._session_memory.get(key, {}).copy()
            if key in self._session_memory:
                self._session_memory.move_to_end(key)
            return state

    def _save_session_memory(self, context: Dict[str, Any], state: Dict[str, str]) -> None:
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
        if re.fullmatch(r"(?:hi|hello|hey)(?: there)?", lower):
            return "Hi! I'm UniGuru. How can I help you?"
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
    def _requests_absent_kb_information(query: str) -> bool:
        return bool(re.search(
            r"\bnot\s+(?:present\s+)?in\s+(?:the\s+)?(?:kb|knowledge\s+base)\b",
            query.casefold(),
        ))

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
        configured = bool(self._llm_url)
        internal_demo = self._llm_url.startswith("internal://")
        return {
            "configured": configured,
            "endpoint": self._llm_url or None,
            "model": self._llm_model or None,
            "internal_demo_mode": internal_demo,
            "available": True,  # safety fallback is always available
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
                verification_status="UNVERIFIED",
                session_id=context_map.get("session_id"),
                governance_allowed=True,
                governance_reason="Conversational response; no knowledge-base evidence required.",
            )
            response.pop("_resolved_route", None)
            response["routing"] = {
                "query_type": QueryRoutingType.GENERAL_LLM_QUERY.value,
                "route": RouteTarget.ROUTE_LLM.value,
                "router_latency_ms": round((time.perf_counter() - started) * 1000, 3),
            }
            return response

        if self._requests_absent_kb_information(query):
            response = self._build_router_contract_response(
                decision="answer",
                answer="I can't verify information that is explicitly absent from my knowledge base. Ask about a specific topic or source, and I'll check the available evidence.",
                reason="The request explicitly states that the requested information is outside the knowledge base.",
                query_type=QueryRoutingType.KNOWLEDGE_QUERY,
                route=RouteTarget.ROUTE_UNIGURU,
                verification_status="UNVERIFIED",
                session_id=context_map.get("session_id"),
                governance_allowed=True,
                governance_reason="No knowledge claim was made without evidence.",
            )
            response.pop("_resolved_route", None)
            response["routing"] = {
                "query_type": QueryRoutingType.KNOWLEDGE_QUERY.value,
                "route": RouteTarget.ROUTE_UNIGURU.value,
                "router_latency_ms": round((time.perf_counter() - started) * 1000, 3),
            }
            return response

        original_query = query
        followup_query = self._followup_query(query, session_state)
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
            return response
        if followup_query:
            query = followup_query

        query_type = self.classify(query=query, context=context_map)
        target = self.select_route(query_type=query_type)
        session_id = context_map.get("session_id")

        if target == RouteTarget.ROUTE_SYSTEM:
            response = self._build_system_block_response(query_type=query_type, session_id=session_id)
        elif target == RouteTarget.ROUTE_WORKFLOW:
            response = self._build_workflow_response(query=query, query_type=query_type, session_id=session_id)
        elif target == RouteTarget.ROUTE_LLM:
            response = self._build_llm_response(
                query=query,
                query_type=query_type,
                session_id=session_id,
                warning=None,
            )
        else:
            response = self._dispatch_to_uniguru(query=query, context=context_map, query_type=query_type)

        resolved_route = str(response.pop("_resolved_route", target.value))
        routing_latency = (time.perf_counter() - started) * 1000
        response["routing"] = {
            "query_type": query_type.value,
            "route": resolved_route,
            "router_latency_ms": round(routing_latency, 3),
        }
        if query_type == QueryRoutingType.KNOWLEDGE_QUERY:
            session_state["last_query"] = session_state.get("last_query") if followup_query else original_query
            self._save_session_memory(context_map, session_state)
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
        if any(re.search(pattern, text) for pattern in _GENERAL_CHAT_PATTERNS):
            return QueryRoutingType.GENERAL_LLM_QUERY
        if any(re.search(pattern, text) for pattern in _CREATIVE_PATTERNS):
            return QueryRoutingType.GENERAL_LLM_QUERY

        upstream_type = classify_query(text)
        if upstream_type in {
            QueryType.KNOWLEDGE_QUERY,
            QueryType.CONCEPT_QUERY,
            QueryType.EXPLANATION_QUERY,
            QueryType.WEB_LOOKUP,
        }:
            # Trust upstream classifier for knowledge-like intents.
            # The previous logic required explicit knowledge regex matches for
            # KNOWLEDGE_QUERY, which incorrectly sent many valid KB queries
            # (e.g. "Types of Karma") to GENERAL_LLM_QUERY.
            return QueryRoutingType.KNOWLEDGE_QUERY
        return QueryRoutingType.GENERAL_LLM_QUERY

    @staticmethod
    def select_route(query_type: QueryRoutingType) -> RouteTarget:
        if query_type == QueryRoutingType.KNOWLEDGE_QUERY:
            return RouteTarget.ROUTE_UNIGURU
        if query_type == QueryRoutingType.SYSTEM_QUERY:
            return RouteTarget.ROUTE_SYSTEM
        if query_type in {QueryRoutingType.WORKFLOW_QUERY, QueryRoutingType.TOOL_QUERY}:
            return RouteTarget.ROUTE_WORKFLOW
        return RouteTarget.ROUTE_LLM

    def _dispatch_to_uniguru(
        self,
        query: str,
        context: Dict[str, Any],
        query_type: QueryRoutingType,
    ) -> Dict[str, Any]:
        session_id = context.get("session_id")
        allow_web = bool(context.get("allow_web", False))
        legacy_type = classify_query(query)
        effective_allow_web = allow_web or legacy_type == QueryType.WEB_LOOKUP

        if self._breaker.should_fallback():
            return self._build_llm_response(
                query=query,
                query_type=query_type,
                session_id=session_id,
                warning="UniGuru latency circuit breaker active. Response delegated to LLM.",
            )

        started = time.perf_counter()
        try:
            response = self._service.ask(
                user_query=query,
                session_id=session_id,
                context=context,
                allow_web_retrieval=effective_allow_web,
            )
        except Exception as exc:
            self._breaker.record_latency((time.perf_counter() - started) * 1000)
            return self._build_llm_response(
                query=query,
                query_type=query_type,
                session_id=session_id,
                warning=f"UniGuru KB path failed ({exc}). Falling back to conversational mode.",
            )
        latency_ms = (time.perf_counter() - started) * 1000

        if not str(response.get("answer") or "").strip():
            self._breaker.record_latency(latency_ms)
            return self._build_llm_response(
                query=query,
                query_type=query_type,
                session_id=session_id,
                warning="UniGuru KB response was empty. Falling back to conversational mode.",
            )

        verification_status = str(response.get("verification_status") or "UNVERIFIED").upper()
        if (
            verification_status == "UNVERIFIED"
            and self._allow_unverified_fallback
            and query_type != QueryRoutingType.KNOWLEDGE_QUERY
        ):
            return self._build_llm_response(
                query=query,
                query_type=query_type,
                session_id=session_id,
                warning="UniGuru could not verify this query. This is an LLM fallback response.",
            )
        return response

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
    ) -> Dict[str, Any]:
        llm_result = self._request_llm(query=query, session_id=session_id)
        answer = llm_result["answer"]
        if warning:
            answer = f"{warning} {answer}"
        return self._build_router_contract_response(
            decision="answer",
            answer=answer,
            reason=llm_result["reason"],
            query_type=query_type,
            route=RouteTarget.ROUTE_LLM,
            verification_status="UNVERIFIED",
            session_id=session_id,
            governance_allowed=True,
            governance_reason=llm_result["governance_reason"],
        )

    def _request_llm(self, query: str, session_id: Optional[str]) -> Dict[str, str]:
        system_prompt = (
            "You are UniGuru, a helpful conversational AI assistant. Answer the user's actual question directly. "
            "For casual conversation, respond naturally. Do not invent knowledge-base facts, citations, or sources; "
            "when evidence is unavailable, say so clearly."
        )
        if self._llm_url.startswith("internal://"):
            return {
                "answer": self._build_local_demo_answer(query),
                "reason": "ROUTE_LLM served by internal demo mode.",
                "governance_reason": "Delegated to internal safety LLM fallback.",
            }

        if not self._llm_url:
            return {
                "answer": self._build_local_demo_answer(query),
                "reason": "ROUTE_LLM selected but UNIGURU_LLM_URL is not configured.",
                "governance_reason": "LLM route unavailable because no endpoint is configured.",
            }

        llm_url_lower = self._llm_url.lower()
        is_openai_chat_style = "/openai/v1/chat/completions" in llm_url_lower or llm_url_lower.endswith("/chat/completions")

        if is_openai_chat_style:
            # Groq/OpenAI-compatible payload.
            sanitized_payload = {
                "model": self._llm_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                "stream": False,
            }
        else:
            payload = {
                "model": self._llm_model or None,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                "prompt": query,
                "query": query,
                "input": query,
                "session_id": session_id,
                "stream": False,
            }
            sanitized_payload = {key: value for key, value in payload.items() if value is not None}
        headers = {"Content-Type": "application/json"}
        if self._llm_api_key:
            headers["Authorization"] = f"Bearer {self._llm_api_key}"

        try:
            response = requests.post(
                self._llm_url,
                json=sanitized_payload,
                headers=headers,
                timeout=self._llm_timeout,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            return {
                "answer": self._build_local_demo_answer(query),
                "reason": "ROUTE_LLM request to configured endpoint failed.",
                "governance_reason": f"LLM route returned an integration failure: {exc}",
            }

        answer = str(
            data.get("answer")
            or data.get("response")
            or data.get("output")
            or data.get("content")
            or (data.get("message") or {}).get("content")
            or ""
        ).strip()
        if not answer and isinstance(data.get("choices"), list) and data["choices"]:
            answer = str(
                (data["choices"][0].get("message") or {}).get("content")
                or data["choices"][0].get("text")
                or ""
            ).strip()

        if not answer:
            answer = self._build_local_demo_answer(query)

        return {
            "answer": answer,
            "reason": "ROUTE_LLM policy applied via configured LLM endpoint.",
            "governance_reason": "Delegated open-chat response through configured LLM service.",
        }

    @staticmethod
    def _build_local_demo_answer(query: str) -> str:
        text = str(query or "").strip()
        lower = text.lower()
        if "joke" in lower:
            body = "Here is one: Why did the developer go broke? Because they used up all their cache."
        elif any(token in lower for token in ("news", "current", "latest", "happening in the world")):
            body = (
                "In demo mode I do not fetch live internet updates, but a good snapshot usually includes "
                "major world news, economic movement, and local developments from trusted sources."
            )
        elif text:
            body = (
                f"{text} can be understood by starting with the core idea, then examples, and then practical usage."
            )
        else:
            body = "Let us start with the basics and build up step by step."
        return f"{SAFE_FALLBACK_PREFIX} {body}"

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
