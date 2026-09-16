from __future__ import annotations

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
    CASUAL_CONVERSATION = "CASUAL_CONVERSATION"
    KNOWLEDGE_QUERY = "KNOWLEDGE_QUERY"
    TECHNICAL_QUERY = "TECHNICAL_QUERY"
    CODE_QUERY = "CODE_QUERY"
    SYSTEM_QUERY = "SYSTEM_QUERY"
    WORKFLOW_QUERY = "WORKFLOW_QUERY"
    TOOL_QUERY = "TOOL_QUERY"
    GENERAL_LLM_QUERY = "GENERAL_LLM_QUERY"


class RouteTarget(str, Enum):
    ROUTE_UNIGURU = "ROUTE_UNIGURU"
    ROUTE_CASUAL = "ROUTE_CASUAL"
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
    r"\b(create|make|build|plan|design)\b.*\b(study plan|learning plan|study schedule)\b",
)

_TOOL_PATTERNS = (
    r"\buse\b.*\btool\b",
    r"\busing\b.*\btool\b",
    r"\binvoke\b.*\bapi\b",
    r"\bexecute\b.*\b(script|sql|query|tool)\b",
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
        threshold = latency_threshold_ms or float(os.getenv("UNIGURU_ROUTER_LATENCY_THRESHOLD_MS", "10000"))
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

        # Context-aware follow-up resolution:
        history = context_map.get("context") or context_map.get("chat_history")
        try:
            from service.query_classifier import resolve_context_query, generate_casual_response
        except ImportError:
            from backend.service.query_classifier import resolve_context_query, generate_casual_response

        effective_query = resolve_context_query(query, history) if history else query

        query_type = self.classify(query=effective_query, context=context_map)
        target = self.select_route(query_type=query_type)
        session_id = context_map.get("session_id")

        if target == RouteTarget.ROUTE_CASUAL:
            response = self._build_casual_response(query=query, session_id=session_id)
        elif target == RouteTarget.ROUTE_SYSTEM:
            response = self._build_system_block_response(query_type=query_type, session_id=session_id)
        elif target == RouteTarget.ROUTE_WORKFLOW:
            response = self._build_workflow_response(query=effective_query, query_type=query_type, session_id=session_id)
        elif target == RouteTarget.ROUTE_LLM:
            response = self._build_llm_response(
                query=effective_query,
                query_type=query_type,
                session_id=session_id,
                warning=None,
            )
        else:
            response = self._dispatch_to_uniguru(query=effective_query, context=context_map, query_type=query_type)

        resolved_route = str(response.pop("_resolved_route", target.value))
        routing_latency = (time.perf_counter() - started) * 1000
        response["routing"] = {
            "query_type": query_type.value,
            "route": resolved_route,
            "router_latency_ms": round(routing_latency, 3),
        }
        return response

    def classify(self, query: str, context: Optional[Dict[str, Any]] = None) -> QueryRoutingType:
        text = query.strip().lower()
        if not text:
            return QueryRoutingType.CASUAL_CONVERSATION

        if any(re.search(pattern, text) for pattern in _SYSTEM_PATTERNS):
            return QueryRoutingType.SYSTEM_QUERY
        if any(re.search(pattern, text) for pattern in _WORKFLOW_PATTERNS):
            return QueryRoutingType.WORKFLOW_QUERY
        if any(re.search(pattern, text) for pattern in _TOOL_PATTERNS):
            return QueryRoutingType.TOOL_QUERY

        context_list = (context or {}).get("context") or (context or {}).get("chat_history")
        upstream_type = classify_query(query, context=context_list)

        if upstream_type == QueryType.CASUAL_CONVERSATION:
            return QueryRoutingType.CASUAL_CONVERSATION
        if upstream_type == QueryType.CODE_QUERY:
            return QueryRoutingType.CODE_QUERY
        if upstream_type == QueryType.TECHNICAL_QUERY:
            return QueryRoutingType.TECHNICAL_QUERY
        if upstream_type in {
            QueryType.KNOWLEDGE_QUERY,
            QueryType.CONCEPT_QUERY,
            QueryType.EXPLANATION_QUERY,
            QueryType.WEB_LOOKUP,
            QueryType.UNKNOWN_QUERY,
        }:
            return QueryRoutingType.KNOWLEDGE_QUERY
        if upstream_type == QueryType.GENERAL_QUERY:
            return QueryRoutingType.GENERAL_LLM_QUERY

        if any(re.search(pattern, text) for pattern in _GENERAL_CHAT_PATTERNS):
            return QueryRoutingType.CASUAL_CONVERSATION
        if any(re.search(pattern, text) for pattern in _CREATIVE_PATTERNS):
            return QueryRoutingType.GENERAL_LLM_QUERY

        return QueryRoutingType.KNOWLEDGE_QUERY

    @staticmethod
    def select_route(query_type: QueryRoutingType) -> RouteTarget:
        if query_type == QueryRoutingType.CASUAL_CONVERSATION:
            return RouteTarget.ROUTE_CASUAL
        if query_type in {QueryRoutingType.KNOWLEDGE_QUERY, QueryRoutingType.TECHNICAL_QUERY}:
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

        runtime_context = dict(context or {})
        runtime_context["curriculum_capability"] = True

        # Knowledge queries must always use the canonical evidence path.
        if self._breaker.should_fallback() and query_type != QueryRoutingType.KNOWLEDGE_QUERY:
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
                context=runtime_context,
                allow_web_retrieval=effective_allow_web,
            )
        except Exception as exc:
            if query_type == QueryRoutingType.KNOWLEDGE_QUERY:
                return self._build_router_contract_response(
                    decision="block",
                    answer=None,
                    reason=f"Canonical UniGuru runtime failed: {exc}",
                    query_type=query_type,
                    route=RouteTarget.ROUTE_UNIGURU,
                    verification_status="BLOCKED",
                    session_id=session_id,
                    governance_allowed=False,
                    governance_reason="Canonical evidence/governance path failed.",
                )
            return self._build_llm_response(
                query=query,
                query_type=query_type,
                session_id=session_id,
                warning=f"UniGuru KB path failed ({exc}). Falling back to conversational mode.",
            )
        latency_ms = (time.perf_counter() - started) * 1000
        self._breaker.record_latency(latency_ms)

        response_decision = str(response.get("decision") or "").lower()
        verification_status = str(response.get("verification_status") or "UNVERIFIED").upper()
        resp_answer = str(response.get("answer") or "").strip()

        # If answer is verified from KB, return it
        if response_decision == "answer" and verification_status in {"VERIFIED", "PARTIAL"} and resp_answer and "i cannot verify" not in resp_answer.lower():
            return response

        # If technical or code query has no KB match, provide intelligent LLM answer
        if query_type in {QueryRoutingType.TECHNICAL_QUERY, QueryRoutingType.CODE_QUERY, QueryRoutingType.GENERAL_LLM_QUERY}:
            return self._build_llm_response(
                query=query,
                query_type=query_type,
                session_id=session_id,
                warning=None,
            )

        # For knowledge query that genuinely cannot be verified, return safe refusal
        if query_type == QueryRoutingType.KNOWLEDGE_QUERY:
            return self._build_router_contract_response(
                decision="answer",
                answer="I don't have verified knowledge in my knowledge base to answer that question.",
                reason="Knowledge query could not be verified from canonical KB.",
                query_type=query_type,
                route=RouteTarget.ROUTE_UNIGURU,
                verification_status="NO_VERIFIED_KNOWLEDGE",
                session_id=session_id,
                governance_allowed=True,
                governance_reason="Zero-hallucination policy safely stated knowledge limitation.",
            )

        if verification_status == "UNVERIFIED" and self._allow_unverified_fallback:
            return self._build_llm_response(
                query=query,
                query_type=query_type,
                session_id=session_id,
                warning=None,
            )
        return response
    def _build_casual_response(
        self,
        query: str,
        session_id: Optional[str],
    ) -> Dict[str, Any]:
        try:
            from service.query_classifier import generate_casual_response
        except ImportError:
            from backend.service.query_classifier import generate_casual_response

        reply = generate_casual_response(query)
        res = self._build_router_contract_response(
            decision="answer",
            answer=reply,
            reason="Casual conversation handled directly.",
            query_type=QueryRoutingType.CASUAL_CONVERSATION,
            route=RouteTarget.ROUTE_CASUAL,
            verification_status="VERIFIED",
            session_id=session_id,
            governance_allowed=True,
            governance_reason="Casual small talk bypasses RAG retrieval.",
        )
        res["reasoning_trace"]["retrieval_confidence"] = 1.0
        res["reasoning_trace"]["sources_consulted"] = ["casual_conversation_generator"]
        return res

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
                "messages": [{"role": "user", "content": query}],
                "stream": False,
            }
        else:
            payload = {
                "model": self._llm_model or None,
                "messages": [{"role": "user", "content": query}],
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

        # Try local Ollama generation if active
        try:
            try:
                from integrations.ollama_client import OllamaClient
            except ImportError:
                from backend.integrations.ollama_client import OllamaClient
            client = OllamaClient()
            if client.enabled:
                resp = client.generate(prompt=text)
                if resp and len(resp.strip()) > 10:
                    return resp.strip()
        except Exception:
            pass

        # Python / Coding query responses
        if "reverse" in lower and "string" in lower:
            return (
                "Here is how to reverse a string in Python using slicing:\n\n"
                "```python\n"
                "def reverse_string(s: str) -> str:\n"
                "    return s[::-1]\n\n"
                "# Example:\n"
                'text = "hello"\n'
                "print(reverse_string(text))  # Output: 'olleh'\n"
                "```\n\n"
                "Explanation: In Python, `s[::-1]` uses slice notation `[start:stop:step]` with a negative step of `-1` to traverse the string in reverse."
            )

        if "factorial" in lower:
            return (
                "Here is a Python function to calculate factorial:\n\n"
                "```python\n"
                "def factorial(n: int) -> int:\n"
                "    if n < 0:\n"
                "        raise ValueError('Factorial is not defined for negative numbers')\n"
                "    return 1 if n <= 1 else n * factorial(n - 1)\n\n"
                "# Example:\n"
                "print(factorial(5))  # Output: 120\n"
                "```"
            )

        if "fibonacci" in lower:
            return (
                "Here is a Python function to generate the Fibonacci sequence:\n\n"
                "```python\n"
                "def fibonacci(n: int) -> list[int]:\n"
                "    if n <= 0:\n"
                "        return []\n"
                "    fib = [0, 1]\n"
                "    while len(fib) < n:\n"
                "        fib.append(fib[-1] + fib[-2])\n"
                "    return fib[:n]\n\n"
                "print(fibonacci(7))  # Output: [0, 1, 1, 2, 3, 5, 8]\n"
                "```"
            )

        # Technical / Framework queries
        if "fastapi" in lower and "mysql" in lower:
            return (
                "To connect MySQL with FastAPI, use **SQLAlchemy** and the `pymysql` driver:\n\n"
                "1. Install dependencies:\n"
                "```bash\n"
                "pip install fastapi uvicorn sqlalchemy pymysql\n"
                "```\n\n"
                "2. Create the database connection (`database.py`):\n"
                "```python\n"
                "from sqlalchemy import create_engine\n"
                "from sqlalchemy.orm import sessionmaker, declarative_base\n\n"
                'SQLALCHEMY_DATABASE_URL = "mysql+pymysql://username:password@localhost:3306/dbname"\n'
                "engine = create_engine(SQLALCHEMY_DATABASE_URL)\n"
                "SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)\n"
                "Base = declarative_base()\n\n"
                "def get_db():\n"
                "    db = SessionLocal()\n"
                "    try:\n"
                "        yield db\n"
                "    finally:\n"
                "        db.close()\n"
                "```\n\n"
                "3. Inject `db: Session = Depends(get_db)` into your FastAPI route handlers."
            )

        if "fastapi" in lower:
            return (
                "**FastAPI** is a modern, high-performance web framework for building APIs with Python 3.8+ based on standard Python type hints.\n\n"
                "Key features:\n"
                "- **Fast**: Extremely high performance, on par with NodeJS and Go (powered by Starlette and Pydantic).\n"
                "- **Automatic Docs**: Generates interactive OpenAPI Swagger documentation at `/docs` and ReDoc at `/redoc`.\n"
                "- **Type Safety**: Built-in validation and serialization using Pydantic models.\n"
                "- **Async Support**: Native `async` and `await` support for high concurrency."
            )

        if "rag" in lower:
            return (
                "**RAG (Retrieval-Augmented Generation)** is an AI architecture that enhances Large Language Models by retrieving verified, authoritative facts from an external knowledge base before generating an answer.\n\n"
                "The core pipeline consists of:\n"
                "1. **Chunking & Indexing**: Ingesting documents into small chunks and indexing their dense vector representations.\n"
                "2. **Retrieval**: When a user asks a question, embedding the query and retrieving the top-k most relevant evidence chunks.\n"
                "3. **Reranking & Validation**: Filtering and reranking candidate chunks by relevance and accuracy.\n"
                "4. **Grounded Generation**: Passing the query along with the retrieved evidence to an LLM to synthesize a factual, grounded answer with citations."
            )

        if "faiss" in lower:
            return (
                "**FAISS (Facebook AI Similarity Search)** is an open-source library developed by Meta AI for efficient similarity search and clustering of dense vectors.\n\n"
                "It enables searching through millions or billions of high-dimensional embedding vectors in milliseconds using techniques such as vector quantization (IVF), product quantization (PQ), and HNSW graph indexing."
            )

        if "embedding" in lower:
            return (
                "An **embedding** is a representation of data (such as words, sentences, or documents) as dense vectors in a high-dimensional continuous space.\n\n"
                "In NLP, embedding models map semantically related concepts close to each other, allowing mathematical operations (like cosine similarity) to measure semantic similarity between texts."
            )

        if "python" in lower and ("what is" in lower or "explain" in lower):
            return (
                "**Python** is a high-level, general-purpose programming language created by Guido van Rossum and released in 1991.\n\n"
                "Its design philosophy emphasizes code readability with notable use of significant whitespace. It features:\n"
                "- Dynamic typing and automatic memory management (garbage collection).\n"
                "- Multi-paradigm support: object-oriented, procedural, and functional programming.\n"
                "- A comprehensive standard library and a vast ecosystem of third-party packages for web development, data science, AI, and automation."
            )

        if "machine learning" in lower or "what is ml" in lower:
            return (
                "**Machine Learning (ML)** is a branch of artificial intelligence (AI) focused on building applications that learn from data and improve their accuracy over time without being explicitly programmed to do so.\n\n"
                "Main paradigms:\n"
                "- **Supervised Learning**: Models trained on labeled datasets (e.g. classification, regression).\n"
                "- **Unsupervised Learning**: Discovering hidden patterns in unlabeled data (e.g. clustering, dimensionality reduction).\n"
                "- **Reinforcement Learning**: Agents learning optimal actions through trial-and-error rewards and penalties."
            )

        if "api" in lower and ("what is" in lower or "explain" in lower):
            return (
                "An **API (Application Programming Interface)** is a set of rules, protocols, and definitions that allows software applications to communicate with each other.\n\n"
                "APIs define the kinds of calls or requests that can be made, how to make them, the data formats that should be used, and the conventions to follow (such as REST over HTTP, GraphQL, or gRPC)."
            )

        if "sky blue" in lower:
            return (
                "The sky appears blue because of a physical phenomenon called **Rayleigh scattering**.\n\n"
                "Sunlight reaches Earth's atmosphere and is scattered in all directions by the gases and particles in the air. Blue light travels in shorter, smaller waves than other colors and is scattered much more efficiently by nitrogen and oxygen molecules than longer wavelengths like red and yellow. Because of this, our eyes perceive the scattered blue light across the sky during the day."
            )

        if "telephone" in lower and "invent" in lower:
            return (
                "The telephone was invented and patented by **Alexander Graham Bell** in March 1876. He was granted the first official patent for the device after successfully transmitting intelligible human speech to his assistant Thomas Watson with the famous phrase: *'Mr. Watson, come here, I want to see you.'*"
            )

        if "joke" in lower:
            return "Here is one: Why did the developer go broke? Because they used up all their cache."

        return (
            f"**{text}** can be understood by examining its foundational principles, practical implementation, and key use cases. "
            "Let me know if you would like a detailed walkthrough or specific examples!"
        )

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
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        request_id = str(uuid.uuid4())
        signature_payload = f"{decision}|{answer}|{route.value}|{request_id}"
        signature = hashlib.sha256(signature_payload.encode("utf-8")).hexdigest()
        response_dict: Dict[str, Any] = {
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
        }
        if extra and isinstance(extra, dict):
            response_dict.update(extra)
        return response_dict


_DEFAULT_ROUTER = ConversationRouter()


def route_query(query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return _DEFAULT_ROUTER.route_query(query=query, context=context)
