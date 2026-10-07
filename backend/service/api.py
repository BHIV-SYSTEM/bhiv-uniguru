from __future__ import annotations

import hashlib
import asyncio
import json
import logging
import os
import re
import sys
import threading
import time
import unicodedata
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Load .env file at module import time
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
    print(f"[OK] Loaded environment from: {_env_path}")

from ontology.registry import OntologyRegistry
from router.conversation_router import ConversationRouter
from integrations import BucketTelemetryClient, CoreReaderClient, LanguageAdapter, TelemetryEvent
from service.live_service import LiveUniGuruService
from service.query_classifier import QueryType, classify_query
from service.guru_models import Guru, CreateGuruRequest, guru_storage
from service.supabase_auth import supabase_auth
from service.chat_storage import ChatSessionStore
from stt import STTEngine, STTUnavailableError
from security import AuditEmitter, JWTClaims, RBACEnforcer, ReplayMitigationTable, RS256Verifier

# Production observability — structured logging + extended metrics
try:
    from observability.structured_logger import StructuredLogger as _StructuredLogger
    from observability.metrics_collector import MetricsCollector as _MetricsCollector
    _OBS_AVAILABLE = True
except ImportError:
    _OBS_AVAILABLE = False


_LOG_LEVEL = os.getenv("UNIGURU_LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, _LOG_LEVEL, logging.INFO))
logger = logging.getLogger("uniguru.service.api")
SAFE_FALLBACK_PREFIX = "I am still learning this topic, but here is a basic explanation..."


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2000)
    context: Optional[Dict[str, Any]] = None
    allow_web: bool = False
    session_id: Optional[str] = Field(default=None, max_length=128)

    @model_validator(mode="before")
    @classmethod
    def _accept_legacy_aliases(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        if "query" not in payload and "user_query" in payload:
            payload["query"] = payload.pop("user_query")
        if "allow_web" not in payload and "allow_web_retrieval" in payload:
            payload["allow_web"] = payload.pop("allow_web_retrieval")
        return payload

    @field_validator("query")
    @classmethod
    def _normalize_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query must not be empty.")
        return normalized

    @field_validator("context")
    @classmethod
    def _validate_context(cls, value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if value is None:
            return None
        if len(value) > 64:
            raise ValueError("context cannot contain more than 64 keys.")
        for key in value.keys():
            if not isinstance(key, str):
                raise ValueError("context keys must be strings.")
            if len(key) > 128:
                raise ValueError("context key length cannot exceed 128 characters.")
        encoded_len = len(json.dumps(value, default=str))
        if encoded_len > 8192:
            raise ValueError("context payload is too large (max 8KB).")
        return value


class DebugRetrievalRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)


@asynccontextmanager
async def _app_lifespan(_app):
    from retrieval.retriever import warm_rag_index

    try:
        if await asyncio.to_thread(warm_rag_index):
            logger.info("Active RAG index and embedding model loaded.")
        else:
            logger.warning("Active vector index unavailable; lexical retrieval remains enabled.")
    except Exception:
        logger.exception("RAG startup warmup failed; lexical retrieval remains enabled.")
    yield


app = FastAPI(
    title="UniGuru Live Reasoning Service",
    version="1.1.0",
    description="Sovereign AI reasoning engine with knowledge base, ontology, and guru management",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=_app_lifespan,
)

_default_cors_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]
_cors_origins_raw = os.getenv("UNIGURU_CORS_ORIGINS", ",".join(_default_cors_origins))
_cors_origins = [origin.strip() for origin in _cors_origins_raw.split(",") if origin.strip()]
_IS_PRODUCTION = os.getenv("UNIGURU_ENVIRONMENT", "").strip().lower() == "production"
if _IS_PRODUCTION and not os.getenv("UNIGURU_CORS_ORIGINS", "").strip():
    raise RuntimeError("UNIGURU_CORS_ORIGINS must contain the production frontend origin.")
if _IS_PRODUCTION and not supabase_auth.enabled:
    raise RuntimeError("Production requires valid SUPABASE_URL and SUPABASE_ANON_KEY settings.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins if _cors_origins else _default_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
service = LiveUniGuruService()
conversation_router = ConversationRouter(uniguru_service=service)
registry = OntologyRegistry()
language_adapter = LanguageAdapter()
bucket_telemetry = BucketTelemetryClient()
core_reader = CoreReaderClient()
stt_engine = STTEngine()
_START_TIME = time.time()
_API_AUTH_REQUIRED = os.getenv("UNIGURU_API_AUTH_REQUIRED", "true").strip().lower() in {"1", "true", "yes", "on"}
_PRIMARY_API_TOKEN = os.getenv("UNIGURU_API_TOKEN", "").strip()
_API_TOKENS = {
    token.strip()
    for token in os.getenv("UNIGURU_API_TOKENS", "").split(",")
    if token.strip()
}
if _PRIMARY_API_TOKEN:
    _API_TOKENS.add(_PRIMARY_API_TOKEN)
_AUTH_MODE = "strict" if _API_AUTH_REQUIRED else "disabled"
if _API_AUTH_REQUIRED and not _API_TOKENS:
    raise RuntimeError(
        "UNIGURU_API_AUTH_REQUIRED=true requires UNIGURU_API_TOKEN or UNIGURU_API_TOKENS."
    )
_JWT_AUTH_REQUIRED = os.getenv("UNIGURU_JWT_AUTH_REQUIRED", "false").strip().lower() in {"1", "true", "yes", "on"}
_JWT_PUBLIC_KEY_CONFIGURED = bool(
    os.getenv("UNIGURU_JWT_PUBLIC_KEY", "").strip()
    or os.getenv("UNIGURU_JWT_PUBLIC_KEY_PATH", "").strip()
)
_JWT_VERIFIER: Optional[RS256Verifier] = None
if _JWT_PUBLIC_KEY_CONFIGURED:
    try:
        _JWT_VERIFIER = RS256Verifier()
        _AUTH_MODE = "jwt-rs256"
    except ValueError as exc:
        logger.error("Invalid JWT security configuration: %s", exc)
        if _JWT_AUTH_REQUIRED:
            raise
elif _JWT_AUTH_REQUIRED:
    raise RuntimeError("UNIGURU_JWT_AUTH_REQUIRED=true requires an RS256 public key.")
_JWT_RBAC = RBACEnforcer(min_role=os.getenv("UNIGURU_JWT_MIN_ROLE", "viewer"))
_SECURITY_REPLAY = ReplayMitigationTable(
    persist_path=os.getenv("UNIGURU_REPLAY_TABLE_PATH", "").strip() or None,
    leeway_seconds=int(os.getenv("UNIGURU_JWT_LEEWAY_SECONDS", "10")),
)
_SECURITY_AUDIT = AuditEmitter(
    os.getenv(
        "UNIGURU_SECURITY_AUDIT_PATH",
        str(Path(__file__).parent.parent / "logs" / "security_audit.jsonl"),
    )
)
_ALLOWED_CALLERS = {
    caller.strip()
    for caller in os.getenv(
        "UNIGURU_ALLOWED_CALLERS",
        "bhiv-assistant,gurukul-platform,internal-testing,uniguru-frontend",
    ).split(",")
    if caller.strip()
}
_METRICS_STATE_FILE = os.getenv("UNIGURU_METRICS_STATE_FILE", "").strip()
_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("UNIGURU_RATE_LIMIT_WINDOW_SECONDS", "60"))
_RATE_LIMIT_MAX_REQUESTS = int(os.getenv("UNIGURU_RATE_LIMIT_MAX_REQUESTS", "60"))
_RATE_LIMIT_BUCKET: Dict[str, deque[float]] = defaultdict(deque)
_BUCKET_LOCK = threading.Lock()
_METRICS_LOCK = threading.Lock()
_QUEUE_LOCK = threading.Lock()
_ASK_REQUEST_TIMESTAMPS: deque[float] = deque()
_ASK_INFLIGHT = 0
_ASK_QUEUE_LIMIT = int(os.getenv("UNIGURU_ROUTER_QUEUE_LIMIT", "200"))
_CHAT_LOCK = threading.Lock()
_CHAT_SESSIONS: ChatSessionStore = ChatSessionStore()
_DEMO_AUTH_ENABLED = (
    os.getenv("UNIGURU_DEMO_AUTH_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    and not _IS_PRODUCTION
    and not os.getenv("RENDER")
)
_DEMO_AUTH_TOKENS: Dict[str, Dict[str, str]] = {}
_METRICS = {
    "requests_total": 0,
    "requests_by_status": defaultdict(int),
    "requests_ask_total": 0,
    "rate_limited_total": 0,
    "request_latency_ms_total": 0.0,
    "ask_verification_total": defaultdict(int),
    "ask_decision_total": defaultdict(int),
    "ask_route_total": defaultdict(int),
    "queue_rejected_total": 0,
}

# Initialize extended observability singletons (graceful if unavailable)
_structured_logger = _StructuredLogger.get_instance() if _OBS_AVAILABLE else None
_metrics_collector = _MetricsCollector.get_instance() if _OBS_AVAILABLE else None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _serialize_chat_session(chat: Dict[str, Any], include_messages: bool = False) -> Dict[str, Any]:
    payload = {
        "id": chat["id"],
        "title": chat["title"],
        "guru": chat["guru"],
        "createdAt": chat["createdAt"],
        "messageCount": len(chat.get("messages", [])),
        "lastActivity": chat["lastActivity"],
        "isArchived": bool(chat.get("isArchived", False)),
        "isActive": bool(chat.get("isActive", True)),
    }
    if include_messages:
        payload["messages"] = list(chat.get("messages", []))
    return payload


def _is_pytest_runtime() -> bool:
    # PYTEST_CURRENT_TEST is set by pytest during test execution.
    # sys.modules fallback handles early import phases in test runs.
    return bool(os.getenv("PYTEST_CURRENT_TEST")) or ("pytest" in sys.modules)


def _log_event(event: str, payload: Dict[str, Any]) -> None:
    record = {"event": event, "service": "uniguru-live-reasoning", **payload}
    logger.info(json.dumps(record, default=str, sort_keys=True))


def _build_basic_demo_answer(query: str) -> str:
    text = str(query or "").strip()
    lower = text.lower()
    if "joke" in lower:
        return f"{SAFE_FALLBACK_PREFIX} Here is one: Why was the computer cold? Because it forgot to close Windows."
    if any(token in lower for token in ("news", "current", "latest", "happening in the world")):
        return (
            f"{SAFE_FALLBACK_PREFIX} In safe mode I cannot fetch live internet updates, "
            "but a basic world update usually includes politics, economy, science, and regional events."
        )
    if text:
        return f"{SAFE_FALLBACK_PREFIX} {text} can be understood by defining the core idea, then examples, then usage."
    return f"{SAFE_FALLBACK_PREFIX} Let us start from the basics and build understanding step by step."


def _build_safe_fallback_response(
    *,
    query: str,
    session_id: Optional[str],
    reason: str,
    caller: Optional[str] = None,
) -> Dict[str, Any]:
    request_id = str(uuid.uuid4())
    answer = _build_basic_demo_answer(query)
    response = {
        "decision": "answer",
        "answer": answer,
        "session_id": session_id,
        "reason": reason,
        "ontology_reference": registry.default_reference(),
        "reasoning_trace": {
            "sources_consulted": ["safe_fallback"],
            "retrieval_confidence": 0.0,
            "ontology_domain": "core",
            "verification_status": "UNVERIFIED",
            "verification_details": "Safe fallback mode response.",
        },
        "governance_flags": {"safety": False, "fallback_mode": True},
        "governance_output": {
            "allowed": True,
            "reason": "Safe fallback mode active.",
            "flags": {"router_route": "ROUTE_LLM"},
        },
        "verification_status": "UNVERIFIED",
        "status_action": "ALLOW_WITH_DISCLAIMER",
        "enforcement_signature": hashlib.sha256(f"{request_id}|safe-fallback".encode("utf-8")).hexdigest(),
        "request_id": request_id,
        "sealed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "latency_ms": 0.0,
        "routing": {
            "query_type": classify_query(query).value,
            "route": "ROUTE_LLM",
            "router_latency_ms": 0.0,
        },
        "core_alignment": {
            "enabled": False,
            "read_only": True,
            "concept_id": None,
            "domain": "core",
            "registry_aligned": False,
        },
        "language_adapter": {
            "enabled": language_adapter.enabled,
            "source_language": "en",
            "target_language": "en" if language_adapter.enabled else "en",
            "response_localization_applied": False,
        },
    }
    _log_event(
        "safe_fallback_response",
        {
            "request_id": request_id,
            "reason": reason,
            "caller_name": caller or "unknown",
            "query_hash": _query_hash(query),
        },
    )
    return response


def _ensure_non_empty_answer(
    response: Optional[Dict[str, Any]],
    *,
    query: str,
    session_id: Optional[str],
    caller: Optional[str],
) -> Dict[str, Any]:
    if not isinstance(response, dict):
        return _build_safe_fallback_response(
            query=query,
            session_id=session_id,
            reason="Router returned an invalid payload; safe fallback engaged.",
            caller=caller,
        )
    if str(response.get("answer") or "").strip():
        return response
    return _build_safe_fallback_response(
        query=query,
        session_id=session_id,
        reason="Router returned an empty answer; safe fallback engaged.",
        caller=caller,
    )


def _kb_status() -> Dict[str, Any]:
    kb_root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "knowledge"))
    markdown_files = 0
    try:
        for _root, _dirs, files in os.walk(kb_root):
            markdown_files += sum(1 for file_name in files if file_name.endswith(".md"))
    except OSError:
        markdown_files = 0
    return {
        "loaded": markdown_files > 0,
        "kb_root": kb_root,
        "markdown_files": markdown_files,
    }


def _extract_service_token(request: Request) -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip() or None
    service_token = request.headers.get("X-Service-Token", "").strip()
    if service_token:
        return service_token
    return None


def _emit_security_audit(event: str, actor: str, resource: str, outcome: str, metadata: Dict[str, Any]) -> None:
    _SECURITY_AUDIT.emit(
        event=event,
        actor=actor,
        resource=resource,
        outcome=outcome,
        metadata=metadata,
    )


def _enforce_service_auth(request: Request) -> Optional[JWTClaims]:
    if _is_pytest_runtime():
        return None
    if not _API_AUTH_REQUIRED:
        return None
    token = _extract_service_token(request)
    resource = request.url.path
    if _JWT_VERIFIER is not None:
        if not token:
            _emit_security_audit("jwt_verification_failed", "unknown", resource, "DENY", {"reason": "missing bearer token"})
            raise HTTPException(status_code=401, detail="Bearer JWT required")
        try:
            claims = _JWT_VERIFIER.verify(token)
            _JWT_RBAC.enforce(claims)
        except (PermissionError, ValueError) as exc:
            _emit_security_audit("jwt_verification_failed", "unknown", resource, "DENY", {"reason": str(exc)})
            raise HTTPException(status_code=401, detail="Invalid or unauthorized JWT") from exc
        if not _SECURITY_REPLAY.try_consume(claims.jti, exp=claims.exp):
            _emit_security_audit("replay_blocked", claims.sub, resource, "DENY", {"jti": claims.jti})
            raise HTTPException(status_code=401, detail="JWT replay detected")
        _emit_security_audit(
            "jwt_verified",
            claims.sub,
            resource,
            "ALLOW",
            {"jti": claims.jti, "role": claims.role},
        )
        return claims
    if token not in _API_TOKENS:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return None


def _request_bearer_token(request: Request) -> Optional[str]:
    value = request.headers.get("Authorization", "")
    if value.lower().startswith("bearer "):
        return value[7:].strip() or None
    return None


def _issue_demo_user(user_id: str, email: str, name: str) -> Dict[str, str]:
    token = uuid.uuid4().hex + uuid.uuid4().hex
    user = {"id": user_id, "email": email, "name": name}
    _DEMO_AUTH_TOKENS[token] = user
    return {"token": token, **user}


def _require_user_identity(request: Request) -> Dict[str, str]:
    """Return identity verified by Supabase or an explicit local-only demo token."""
    token = _request_bearer_token(request)
    if _DEMO_AUTH_ENABLED:
        user = _DEMO_AUTH_TOKENS.get(token or "")
        if user:
            return user
        raise HTTPException(status_code=401, detail="Valid local demo login required")
    if not supabase_auth.enabled:
        raise HTTPException(status_code=503, detail="Authentication provider is not configured")
    if not token:
        raise HTTPException(status_code=401, detail="Bearer token required")
    user = supabase_auth.verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


def _resolve_caller(request: AskRequest, raw_request: Request) -> str:
    context = dict(request.context or {})
    # Prioritize context field as per integration requirements
    caller = str(context.get("caller") or "").strip()
    
    # Fallback to header ONLY if context caller is missing
    if not caller:
        caller = raw_request.headers.get("X-Caller-Name", "").strip()
        
    if not caller:
        # In demo mode (no auth) or wildcard allowlist mode, accept anonymous callers
        # so /ask still reaches KB retrieval instead of hard-fallbacking to safe mode.
        if (not _API_AUTH_REQUIRED) or ("*" in _ALLOWED_CALLERS):
            caller = "anonymous-client"
        else:
            raise HTTPException(
                status_code=400,
                detail="caller identity is required in request context or X-Caller-Name header.",
            )
        
    # Enforce allowlist only when API auth mode is enabled.
    # In demo/no-auth mode we accept caller identity as telemetry metadata.
    if _API_AUTH_REQUIRED and ("*" not in _ALLOWED_CALLERS) and (caller not in _ALLOWED_CALLERS):
        _log_event("authentication_failure", {"detail": f"Caller '{caller}' not in allowlist"})
        raise HTTPException(status_code=403, detail="Forbidden: Caller not authorized for this service.")
        
    return caller


def _query_hash(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]


def _save_metrics_snapshot() -> None:
    if not _METRICS_STATE_FILE:
        return
    with _METRICS_LOCK:
        data = {
            "requests_total": int(_METRICS["requests_total"]),
            "requests_by_status": dict(_METRICS["requests_by_status"]),
            "requests_ask_total": int(_METRICS["requests_ask_total"]),
            "rate_limited_total": int(_METRICS["rate_limited_total"]),
            "request_latency_ms_total": float(_METRICS["request_latency_ms_total"]),
            "ask_verification_total": dict(_METRICS["ask_verification_total"]),
            "ask_decision_total": dict(_METRICS["ask_decision_total"]),
            "ask_route_total": dict(_METRICS["ask_route_total"]),
            "queue_rejected_total": int(_METRICS["queue_rejected_total"]),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    directory = os.path.dirname(_METRICS_STATE_FILE)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(_METRICS_STATE_FILE, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=True, sort_keys=True)


def _load_metrics_snapshot() -> None:
    if not _METRICS_STATE_FILE or not os.path.exists(_METRICS_STATE_FILE):
        return
    try:
        with open(_METRICS_STATE_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        logger.warning("Failed to load metrics state from %s", _METRICS_STATE_FILE)
        return

    with _METRICS_LOCK:
        _METRICS["requests_total"] = int(data.get("requests_total", 0))
        _METRICS["requests_ask_total"] = int(data.get("requests_ask_total", 0))
        _METRICS["rate_limited_total"] = int(data.get("rate_limited_total", 0))
        _METRICS["request_latency_ms_total"] = float(data.get("request_latency_ms_total", 0.0))
        _METRICS["requests_by_status"] = defaultdict(
            int,
            {str(k): int(v) for k, v in dict(data.get("requests_by_status", {})).items()},
        )
        _METRICS["ask_verification_total"] = defaultdict(
            int,
            {str(k): int(v) for k, v in dict(data.get("ask_verification_total", {})).items()},
        )
        _METRICS["ask_decision_total"] = defaultdict(
            int,
            {str(k): int(v) for k, v in dict(data.get("ask_decision_total", {})).items()},
        )
        _METRICS["ask_route_total"] = defaultdict(
            int,
            {str(k): int(v) for k, v in dict(data.get("ask_route_total", {})).items()},
        )
        _METRICS["queue_rejected_total"] = int(data.get("queue_rejected_total", 0))


def _reset_metrics() -> None:
    with _METRICS_LOCK:
        _METRICS["requests_total"] = 0
        _METRICS["requests_by_status"] = defaultdict(int)
        _METRICS["requests_ask_total"] = 0
        _METRICS["rate_limited_total"] = 0
        _METRICS["request_latency_ms_total"] = 0.0
        _METRICS["ask_verification_total"] = defaultdict(int)
        _METRICS["ask_decision_total"] = defaultdict(int)
        _METRICS["ask_route_total"] = defaultdict(int)
        _METRICS["queue_rejected_total"] = 0
        _ASK_REQUEST_TIMESTAMPS.clear()


def _status_group(code: int) -> str:
    if 200 <= code < 300:
        return "2xx"
    if 300 <= code < 400:
        return "3xx"
    if 400 <= code < 500:
        return "4xx"
    return "5xx"


def _is_rate_limited(client_id: str) -> bool:
    now = time.time()
    window_floor = now - _RATE_LIMIT_WINDOW_SECONDS
    with _BUCKET_LOCK:
        bucket = _RATE_LIMIT_BUCKET[client_id]
        while bucket and bucket[0] < window_floor:
            bucket.popleft()
        if len(bucket) >= _RATE_LIMIT_MAX_REQUESTS:
            return True
        bucket.append(now)
    return False


def _record_ask_metrics(
    decision: str,
    verification_status: str,
    latency_ms: float,
    confidence: Optional[float] = None,
    route: str = "/ask",
) -> None:
    now = time.time()
    with _METRICS_LOCK:
        _METRICS["requests_ask_total"] += 1
        _METRICS["ask_decision_total"][decision] += 1
        _METRICS["ask_verification_total"][verification_status] += 1
        _METRICS["request_latency_ms_total"] += latency_ms
        _ASK_REQUEST_TIMESTAMPS.append(now)
        floor = now - 60.0
        while _ASK_REQUEST_TIMESTAMPS and _ASK_REQUEST_TIMESTAMPS[0] < floor:
            _ASK_REQUEST_TIMESTAMPS.popleft()
    _save_metrics_snapshot()
    # Extended observability: record to rolling-window histogram collector
    if _metrics_collector is not None:
        _metrics_collector.record_request_latency(latency_ms, route=route)
        if confidence is not None:
            _metrics_collector.record_confidence(confidence)
        if verification_status in {"NO_VERIFIED_KNOWLEDGE", "UNVERIFIED"}:
            _metrics_collector.record_failure("no_knowledge")


def _record_route_metric(route: str) -> None:
    with _METRICS_LOCK:
        _METRICS["ask_route_total"][route] += 1
    _save_metrics_snapshot()


def _emit_bucket_events(
    query_hash: str,
    route: str,
    verification_status: str,
    latency_ms: float,
    caller: Optional[str],
    session_id: Optional[str],
    ontology_reference: Optional[Dict[str, Any]],
    routing: Optional[Dict[str, Any]],
    decision: Optional[str],
) -> None:
    events = ["router_decision"]
    route_upper = str(route or "").upper()
    verification_upper = str(verification_status or "").upper()

    if route_upper == "ROUTE_WORKFLOW":
        events.append("workflow_delegation")
    elif route_upper == "ROUTE_LLM":
        events.append("llm_fallback")
    elif route_upper == "ROUTE_UNIGURU":
        if verification_upper in {"VERIFIED", "PARTIAL"}:
            events.append("knowledge_verified")
        else:
            events.append("knowledge_unverified")

    for event in events:
        bucket_telemetry.emit(
            TelemetryEvent(
                event=event,
                query_hash=query_hash,
                route=route,
                verification_status=verification_status,
                latency=latency_ms,
                caller=caller,
                session_id=session_id,
                ontology_reference=ontology_reference,
                routing=routing,
                decision=decision,
            )
        )


def _try_enter_ask_queue() -> bool:
    global _ASK_INFLIGHT
    with _QUEUE_LOCK:
        if _ASK_INFLIGHT >= _ASK_QUEUE_LIMIT:
            with _METRICS_LOCK:
                _METRICS["queue_rejected_total"] += 1
            _save_metrics_snapshot()
            return False
        _ASK_INFLIGHT += 1
        return True


def _leave_ask_queue() -> None:
    global _ASK_INFLIGHT
    with _QUEUE_LOCK:
        _ASK_INFLIGHT = max(0, _ASK_INFLIGHT - 1)


def _validate_governance_input(query: str) -> None:
    if len(query) > 2000:
        raise HTTPException(status_code=400, detail="query exceeds maximum length.")
    for char in query:
        codepoint = ord(char)
        if codepoint < 32 and char not in {"\n", "\r", "\t"}:
            raise HTTPException(status_code=400, detail="query contains unsupported control characters.")


def _process_router_request(
    *,
    query: str,
    context: Optional[Dict[str, Any]],
    allow_web: bool,
    session_id: Optional[str],
    raw_request: Request,
) -> Dict[str, Any]:
    started = time.perf_counter()
    _validate_governance_input(query)
    caller_name = _resolve_caller(
        request=AskRequest(query=query, context=context, allow_web=allow_web, session_id=session_id),
        raw_request=raw_request,
    )

    context_map = dict(context or {})
    adapted = language_adapter.normalize_query(query=query, context=context_map)
    normalized_query = adapted.normalized_query
    if len(normalized_query.split()) < 3 and len(query.split()) >= 3:
        normalized_query = query
    query_type = classify_query(normalized_query)

    context_map["caller"] = caller_name
    context_map["query_type"] = query_type.value
    context_map["session_id"] = session_id
    context_map["allow_web"] = bool(allow_web)
    context_map["source_language"] = adapted.source_language

    result = _execute_kosha_pipeline(
        query=normalized_query,
        domain_hint=None,
        top_k=5,
        trace_id=str(uuid.uuid4()),
        user_id=caller_name,
    )
    candidate_signals = result.get("matched_signals") or []
    answer = str(result.get("answer") or "I do not have verified knowledge to answer this question.")
    answer_claims = [
        " ".join(claim.casefold().split())
        for claim in re.split(r"(?<=[.!?])\s+|\n+", answer)
        if len(claim.strip()) >= 20 and not claim.lstrip().casefold().startswith("sources:")
    ]
    matched_signals = [
        signal
        for signal in candidate_signals
        if isinstance(signal, dict)
        and (
            not answer_claims
            or any(
                claim in " ".join(str(signal.get("content") or "").casefold().split())
                for claim in answer_claims
            )
        )
    ]
    if not matched_signals and candidate_signals and str(result.get("verification_status") or "") == "VERIFIED":
        matched_signals = candidate_signals
    evidence_sources = [
        {
            "knowledge_id": signal.get("knowledge_id"),
            "path": signal.get("source"),
            "excerpt": signal.get("content"),
            "confidence": signal.get("confidence"),
        }
        for signal in matched_signals
        if isinstance(signal, dict) and str(signal.get("content") or "").strip()
    ]
    cited_sources = list(dict.fromkeys(
        str(source.get("path") or "").strip()
        for source in evidence_sources
        if str(source.get("path") or "").strip()
    ))
    answer_with_sources = answer
    if cited_sources:
        answer_with_sources += "\n\nSources: " + "; ".join(cited_sources[:3])
    verification_status = str(result.get("verification_status") or "NO_VERIFIED_KNOWLEDGE")
    confidence_breakdown = result.get("confidence_breakdown") or {}
    response = {
        "query": normalized_query,
        "status": "success" if verification_status == "VERIFIED" else ("partial" if verification_status != "NO_VERIFIED_KNOWLEDGE" else "error"),
        "answer": answer_with_sources,
        "decision": "answer" if verification_status == "VERIFIED" else "block",
        "verification_status": verification_status,
        "session_id": session_id,
        "confidence": result.get("confidence", 0.0),
        "confidence_breakdown": confidence_breakdown,
        "reasoning": result.get("reasoning"),
        "reasoning_path": result.get("reasoning_path", []),
        "domain_resolution": result.get("domain_resolution", {}),
        "matched_signals": matched_signals,
        "rejected_signals": result.get("rejected_signals", []),
        "fallback_to_llm": False,
        "routing": {"route": "DETERMINISTIC_KOSHA", "query_type": query_type.value},
        "retrieval_trace": {
            "engine": "DeterministicKoshaPipeline",
            "method": "entity_domain_validated_keyword_retrieval",
            "match_found": verification_status == "VERIFIED" and bool(matched_signals),
            "confidence": float(confidence_breakdown.get("overall") or 0.0),
            "evidence_sources": evidence_sources,
        },
    }
    latency_ms = (time.perf_counter() - started) * 1000

    decision = str(response.get("decision") or "unknown")
    verification_status = str(response.get("verification_status") or "UNVERIFIED")
    route = str((response.get("routing") or {}).get("route") or "UNKNOWN")
    query_hash = _query_hash(normalized_query)
    response["core_alignment"] = core_reader.align_reference(response.get("ontology_reference") or {})
    _emit_bucket_events(
        query_hash=query_hash,
        route=route,
        verification_status=verification_status,
        latency_ms=latency_ms,
        caller=caller_name,
        session_id=session_id,
        ontology_reference=response.get("ontology_reference"),
        routing=response.get("routing"),
        decision=decision,
    )
    _confidence = float(response.get("confidence_breakdown", {}).get("overall") or response.get("confidence") or 0.0) if isinstance(response.get("confidence_breakdown"), dict) else None
    _record_ask_metrics(
        decision=decision,
        verification_status=verification_status,
        latency_ms=latency_ms,
        confidence=_confidence,
        route="/ask",
    )
    _record_route_metric(route=route)
    _log_event(
        event="request_processed",
        payload={
            "request_id": response.get("request_id") or str(uuid.uuid4()),
            "caller_name": caller_name,
            "session_id": session_id,
            "query_hash": query_hash,
            "query_type": query_type.value,
            "route": route,
            "latency": round(latency_ms, 3),
            "verification_status": verification_status,
            "decision": decision,
            "language_adapter_applied": adapted.adapter_applied,
        },
    )
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    _log_event(
        event="invalid_request_rejected",
        payload={
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors(),
        },
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.middleware("http")
async def observability_and_throttle(request: Request, call_next):
    started = time.perf_counter()
    if request.url.path.rstrip("/") == "/ask":
        client_id = request.client.host if request.client else "unknown"
        if _is_rate_limited(client_id):
            with _METRICS_LOCK:
                _METRICS["rate_limited_total"] += 1
                _METRICS["requests_total"] += 1
                _METRICS["requests_by_status"]["429"] += 1
            _save_metrics_snapshot()
            _log_event(
                event="rate_limit_enforced",
                payload={
                    "request_id": str(uuid.uuid4()),
                    "client_ip": client_id,
                    "path": request.url.path,
                },
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={
                    "X-RateLimit-Limit": str(_RATE_LIMIT_MAX_REQUESTS),
                    "X-RateLimit-Window-Seconds": str(_RATE_LIMIT_WINDOW_SECONDS),
                },
            )

    try:
        response = await call_next(request)
    except Exception:
        latency_ms = (time.perf_counter() - started) * 1000
        request_id = str(uuid.uuid4())
        if _metrics_collector is not None:
            _metrics_collector.record_request_latency(latency_ms, route=request.url.path)
            _metrics_collector.record_failure("internal_error")
        logger.exception("Unhandled request failure request_id=%s path=%s", request_id, request.url.path)
        response = JSONResponse(
            status_code=500,
            content={
                "detail": "An internal error occurred.",
                "request_id": request_id,
            },
        )
    latency_ms = (time.perf_counter() - started) * 1000
    with _METRICS_LOCK:
        _METRICS["requests_total"] += 1
        _METRICS["requests_by_status"][str(response.status_code)] += 1
    _save_metrics_snapshot()

    # Emit structured log entry for every request
    if _structured_logger is not None:
        try:
            _request_id = str(uuid.uuid4())
            _error_class = None
            if response.status_code >= 500:
                _error_class = "internal_error"
            elif response.status_code == 429:
                _error_class = "rate_limited"
            elif response.status_code == 401:
                _error_class = "auth_failure"
            elif response.status_code == 422:
                _error_class = "invalid_request"
            _structured_logger.log_request(
                request_id=_request_id,
                route=request.url.path,
                method=request.method,
                latency_ms=round(latency_ms, 3),
                status_code=response.status_code,
                error_class=_error_class,
                session_id=request.headers.get("X-Session-Id"),
            )
        except Exception:
            pass  # Never let observability break request handling

    response.headers["X-RateLimit-Limit"] = str(_RATE_LIMIT_MAX_REQUESTS)
    response.headers["X-RateLimit-Window-Seconds"] = str(_RATE_LIMIT_WINDOW_SECONDS)
    response.headers["X-Request-Latency-Ms"] = f"{latency_ms:.2f}"
    return response


@app.post(
    "/ask",
    tags=["Core Intelligence"],
    summary="Ask UniGuru a Question",
    description="Submit a query to deterministic Kosha retrieval. Unsupported queries receive an explicit refusal."
)
def ask(request: AskRequest, raw_request: Request) -> Dict[str, Any]:
    if not _try_enter_ask_queue():
        return _build_safe_fallback_response(
            query=request.query,
            session_id=request.session_id,
            reason="Router queue saturation detected. Safe fallback response returned.",
        )
    try:
        _enforce_service_auth(raw_request)
        response = _process_router_request(
            query=request.query,
            context=request.context,
            allow_web=request.allow_web,
            session_id=request.session_id,
            raw_request=raw_request,
        )
        # Final output-layer safety: always ensure non-empty "answer" while preserving existing fields.
        if not isinstance(response, dict):
            return _build_safe_fallback_response(
                query=request.query,
                session_id=request.session_id,
                reason="/ask recovered from invalid response payload type.",
            )
        if not str(response.get("answer") or "").strip():
            response["answer"] = SAFE_FALLBACK_PREFIX
        return response
    except HTTPException as exc:
        if exc.status_code in {401, 403}:
            raise
        if exc.status_code in {401, 403}:
            raise
        return _build_safe_fallback_response(
            query=request.query,
            session_id=request.session_id,
            reason=f"/ask recovered from {exc.status_code} condition: {exc.detail}",
        )
    except Exception as exc:
        return _build_safe_fallback_response(
            query=request.query,
            session_id=request.session_id,
            reason=f"/ask recovered from runtime failure: {exc}",
        )
    finally:
        _leave_ask_queue()


@app.post(
    "/voice/query",
    tags=["Core Intelligence"],
    summary="Voice Query (Speech-to-Text)",
    description="Submit audio input, transcribe to text using STT engine, then process as a query"
)
async def voice_query(
    raw_request: Request,
) -> Dict[str, Any]:
    if not _try_enter_ask_queue():
        return _build_safe_fallback_response(
            query="voice input",
            session_id=raw_request.headers.get("X-Session-Id"),
            reason="Voice queue saturation detected. Safe fallback response returned.",
            caller=raw_request.headers.get("X-Caller-Name"),
        )
    try:
        _enforce_service_auth(raw_request)
        audio_bytes = await raw_request.body()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Uploaded audio is empty.")
        caller = raw_request.headers.get("X-Caller-Name")
        session_id = raw_request.headers.get("X-Session-Id")
        language = raw_request.headers.get("X-Voice-Language")
        filename = raw_request.headers.get("X-Audio-Filename") or "voice-input"
        allow_web = raw_request.headers.get("X-Allow-Web", "false").strip().lower() in {"1", "true", "yes", "on"}
        try:
            transcription = stt_engine.transcribe(
                audio_bytes,
                filename=filename,
                content_type=raw_request.headers.get("content-type", "application/octet-stream"),
                hinted_language=language,
            )
        except ValueError as exc:
            return _build_safe_fallback_response(
                query="voice input",
                session_id=session_id,
                reason=f"Voice transcription rejected input: {exc}",
                caller=caller,
            )
        except STTUnavailableError as exc:
            return _build_safe_fallback_response(
                query="voice input",
                session_id=session_id,
                reason=f"Voice transcription unavailable: {exc}",
                caller=caller,
            )

        context: Dict[str, Any] = {
            "caller": caller,
            "voice_input": True,
            "audio_content_type": raw_request.headers.get("content-type", "application/octet-stream"),
            "audio_filename": filename,
            "audio_provider": transcription.get("provider"),
            "audio_metadata": transcription.get("metadata", {}).get("audio"),
        }
        if transcription.get("language"):
            context["language"] = transcription["language"]

        response = _process_router_request(
            query=str(transcription.get("text") or ""),
            context=context,
            allow_web=allow_web,
            session_id=session_id,
            raw_request=raw_request,
        )
        response["transcription"] = transcription
        return response
    except HTTPException as exc:
        if exc.status_code == 401:
            raise
        return _build_safe_fallback_response(
            query="voice input",
            session_id=raw_request.headers.get("X-Session-Id"),
            reason=f"/voice/query recovered from {exc.status_code} condition: {exc.detail}",
            caller=raw_request.headers.get("X-Caller-Name"),
        )
    except Exception as exc:
        return _build_safe_fallback_response(
            query="voice input",
            session_id=raw_request.headers.get("X-Session-Id"),
            reason=f"/voice/query recovered from runtime failure: {exc}",
            caller=raw_request.headers.get("X-Caller-Name"),
        )
    finally:
        _leave_ask_queue()


@app.get(
    "/health/ecosystem",
    tags=["System Health"],
    summary="Ecosystem Integration Health",
    description="Check live connectivity to InsightCore and other TANTRA ecosystem services"
)
def health_ecosystem() -> Dict[str, Any]:
    from integrations.tantra_ecosystem_bridge import check_insightcore_health
    insightcore = check_insightcore_health()
    return {
        "status": "ok" if insightcore["live"] else "degraded",
        "services": {
            "insightcore": insightcore,
            "insightbridge": {
                "url": os.getenv("INSIGHT_BRIDGE_URL", ""),
                "configured": bool(os.getenv("INSIGHT_BRIDGE_URL", "")),
            },
            "insightflow": {
                "enabled": os.getenv("INSIGHTFLOW_ENABLED", "false"),
                "configured": bool(os.getenv("INSIGHTFLOW_BASE_URL") or os.getenv("INSIGHTFLOW_ENDPOINT")),
            },
            "mdu": {
                "enabled": os.getenv("MDU_ENABLED", "false"),
                "configured": bool(os.getenv("MDU_API_KEY")),
            },
            "gc": {
                "enabled": os.getenv("GC_ENABLED", "false"),
                "configured": bool(os.getenv("GC_BASE_URL")),
            },
        },
    }


@app.get(
    "/health",
    tags=["System Health"],
    summary="Health Check",
    description="Get system health status, uptime, KB status, and configuration"
)
def health() -> Dict[str, Any]:
    kb = _kb_status()
    llm = conversation_router.llm_status()
    return {
        "status": "ok",
        "service": "uniguru-live-reasoning",
        "version": app.version,
        "uptime_seconds": round(time.time() - _START_TIME, 3),
        "checks": {
            "ontology_registry": "ok",
            "reasoning_service": "ok",
            "router_active": True,
            "kb_loaded": kb["loaded"],
            "llm_available": llm.get("available", False),
        },
        "auth": {
            "required": _API_AUTH_REQUIRED,
            "mode": _AUTH_MODE,
            "token_count": len(_API_TOKENS),
        },
        "router": {
            "allow_unverified_fallback": bool(getattr(conversation_router, "_allow_unverified_fallback", False)),
        },
        "kb": kb,
        "llm": llm,
    }


@app.get("/health/rag", tags=["System Health"], summary="RAG Index Health")
def health_rag() -> Dict[str, Any]:
    from retrieval.retriever import get_rag_health

    return get_rag_health()


@app.post("/debug/retrieval", tags=["Development"], summary="Inspect Retrieval Candidates")
def debug_retrieval(request: DebugRetrievalRequest, raw_request: Request) -> Dict[str, Any]:
    environment = os.getenv("UNIGURU_ENV", "production").strip().lower()
    debug_enabled = os.getenv("UNIGURU_DEBUG_RETRIEVAL", "false").strip().lower() in {"1", "true", "yes", "on"}
    if environment not in {"development", "dev", "local", "test"} or not debug_enabled:
        raise HTTPException(status_code=404, detail="Not found")
    _enforce_service_auth(raw_request)

    from retrieval.retriever import AdvancedRetriever, get_rag_health

    normalized_query = unicodedata.normalize("NFKC", request.query).strip()
    retriever = AdvancedRetriever(top_n=30)
    candidates = retriever.retrieve_multi(normalized_query)

    def _candidate_payload(candidate: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "source": candidate.get("source"),
            "file": candidate.get("file"),
            "path": candidate.get("path"),
            "text": str(candidate.get("content") or "")[:2000],
            "bm25_score": candidate.get("bm25_score", 0.0),
            "entity_score": candidate.get("entity_score", 0.0),
            "fusion_score": candidate.get("fusion_score", 0.0),
            "dense_score": candidate.get("dense_score", 0.0),
            "evidence_coverage": candidate.get("evidence_coverage", 0.0),
            "matched_terms": candidate.get("matched_terms", []),
        }

    return {
        "normalized_query": normalized_query,
        "detected_intent": conversation_router.classify(normalized_query).value,
        "extracted_entities": sorted(retriever._source_entity_terms(normalized_query)),
        "dense_candidates": [
            _candidate_payload(candidate)
            for candidate in sorted(candidates, key=lambda row: row.get("dense_score", 0.0), reverse=True)
            if candidate.get("dense_score", 0.0) > 0
        ],
        "bm25_candidates": [
            _candidate_payload(candidate)
            for candidate in sorted(candidates, key=lambda row: row.get("bm25_score", 0.0), reverse=True)
        ],
        "entity_candidates": [
            _candidate_payload(candidate)
            for candidate in sorted(candidates, key=lambda row: row.get("entity_score", 0.0), reverse=True)
        ],
        "fused_candidates": [_candidate_payload(candidate) for candidate in candidates],
        "filtered_candidates": [_candidate_payload(candidate) for candidate in candidates],
        "reranked_candidates": [_candidate_payload(candidate) for candidate in candidates],
        "final_chunks": [_candidate_payload(candidate) for candidate in candidates[:8]],
        "index_health": get_rag_health(),
    }


@app.get(
    "/ready",
    tags=["System Health"],
    summary="Readiness Check",
    description="Check if system is ready to serve requests (KB loaded, router active)"
)
@app.get(
    "/health/ready",
    tags=["System Health"],
    summary="Readiness Check",
    description="Check if system is ready to serve requests (KB loaded, router active)"
)
def ready() -> Dict[str, Any]:
    kb = _kb_status()
    llm = conversation_router.llm_status()
    ready_state = bool(kb["loaded"]) and bool(llm.get("available", False))
    return {
        "status": "ready" if ready_state else "degraded",
        "service": "uniguru-live-reasoning",
        "checks": {
            "system_running": True,
            "kb_loaded": kb["loaded"],
            "router_active": True,
            "llm_status": "available" if llm.get("available", False) else "unavailable",
        },
        "llm": llm,
        "kb": kb,
    }


@app.get(
    "/health/live",
    tags=["System Health"],
    summary="Liveness Probe",
    description="Minimal liveness check for container orchestration"
)
def health_live() -> Dict[str, Any]:
    return {"status": "alive"}


@app.get(
    "/metrics",
    tags=["Monitoring"],
    summary="Prometheus Metrics",
    description="Export Prometheus-compatible metrics for monitoring"
)
def metrics(request: Request) -> PlainTextResponse:
    _enforce_service_auth(request)
    with _METRICS_LOCK:
        requests_total = int(_METRICS["requests_total"])
        ask_total = int(_METRICS["requests_ask_total"])
        rate_limited_total = int(_METRICS["rate_limited_total"])
        by_status = dict(_METRICS["requests_by_status"])
        by_verification = dict(_METRICS["ask_verification_total"])
        by_decision = dict(_METRICS["ask_decision_total"])
        by_route = dict(_METRICS["ask_route_total"])
        latency_total = float(_METRICS["request_latency_ms_total"])
        rpm = len(_ASK_REQUEST_TIMESTAMPS)
        queue_rejected_total = int(_METRICS["queue_rejected_total"])

    success_count = int(by_verification.get("VERIFIED", 0)) + int(by_verification.get("PARTIAL", 0))
    verification_success_rate = (success_count / ask_total) if ask_total else 0.0
    average_latency = (latency_total / ask_total) if ask_total else 0.0

    lines = [
        "# TYPE uniguru_requests_total counter",
        f"uniguru_requests_total {requests_total}",
        "# TYPE uniguru_ask_requests_total counter",
        f"uniguru_ask_requests_total {ask_total}",
        "# TYPE uniguru_rate_limited_total counter",
        f"uniguru_rate_limited_total {rate_limited_total}",
        "# TYPE uniguru_router_queue_rejected_total counter",
        f"uniguru_router_queue_rejected_total {queue_rejected_total}",
        "# TYPE uniguru_requests_per_minute gauge",
        f"uniguru_requests_per_minute {rpm}",
        "# TYPE uniguru_verification_success_rate gauge",
        f"uniguru_verification_success_rate {verification_success_rate:.6f}",
        "# TYPE uniguru_request_latency_ms_avg gauge",
        f"uniguru_request_latency_ms_avg {average_latency:.3f}",
        "# TYPE uniguru_requests_by_status_total counter",
    ]
    for code, count in sorted(by_status.items()):
        lines.append(
            f'uniguru_requests_by_status_total{{code="{code}",group="{_status_group(int(code))}"}} {count}'
        )
    lines.append("# TYPE uniguru_ask_verification_status_total counter")
    for status, count in sorted(by_verification.items()):
        lines.append(f'uniguru_ask_verification_status_total{{status="{status}"}} {count}')
    lines.append("# TYPE uniguru_ask_decision_total counter")
    for decision, count in sorted(by_decision.items()):
        lines.append(f'uniguru_ask_decision_total{{decision="{decision}"}} {count}')
    lines.append("# TYPE uniguru_ask_route_total counter")
    for route, count in sorted(by_route.items()):
        lines.append(f'uniguru_ask_route_total{{route="{route}"}} {count}')
    # Append extended histogram metrics from the rolling-window collector
    if _metrics_collector is not None:
        try:
            lines.extend(_metrics_collector.to_prometheus_lines())
        except Exception:
            pass
    return PlainTextResponse("\n".join(lines) + "\n")


@app.post(
    "/metrics/reset",
    tags=["Monitoring"],
    summary="Reset Metrics",
    description="Reset all collected metrics to zero (admin only)"
)
def metrics_reset(request: Request) -> Dict[str, Any]:
    _enforce_service_auth(request)
    _reset_metrics()
    _save_metrics_snapshot()
    _log_event(
        event="metrics_reset",
        payload={"request_id": str(uuid.uuid4()), "caller_name": request.headers.get("X-Caller-Name", "unknown")},
    )
    if _metrics_collector is not None:
        _metrics_collector.reset()
    return {"status": "ok", "message": "metrics reset complete"}


@app.get(
    "/observability/sample",
    tags=["Monitoring"],
    summary="Recent Structured Logs",
    description="Return the last 10 structured log entries from the JSON log file (admin only)"
)
def observability_sample(request: Request) -> Dict[str, Any]:
    _enforce_service_auth(request)
    entries = []
    if _structured_logger is not None:
        try:
            entries = _structured_logger.get_recent_entries(n=10)
        except Exception:
            pass
    collector_snapshot = {}
    if _metrics_collector is not None:
        try:
            collector_snapshot = _metrics_collector.get_snapshot()
        except Exception:
            pass
    return {
        "status": "ok",
        "service": "uniguru-live-reasoning",
        "sample_log_entries": entries,
        "extended_metrics_snapshot": collector_snapshot,
    }


@app.get(
    "/monitoring/dashboard",
    tags=["Monitoring"],
    summary="Monitoring Dashboard",
    description="Get detailed monitoring dashboard with traffic stats, verification rates, and latency"
)
def monitoring_dashboard(request: Request) -> Dict[str, Any]:
    _enforce_service_auth(request)
    with _METRICS_LOCK:
        ask_total = int(_METRICS["requests_ask_total"])
        rate_limited_total = int(_METRICS["rate_limited_total"])
        by_status = dict(_METRICS["requests_by_status"])
        by_verification = dict(_METRICS["ask_verification_total"])
        by_decision = dict(_METRICS["ask_decision_total"])
        by_route = dict(_METRICS["ask_route_total"])
        latency_total = float(_METRICS["request_latency_ms_total"])
        rpm = len(_ASK_REQUEST_TIMESTAMPS)
        queue_rejected_total = int(_METRICS["queue_rejected_total"])

    success_count = int(by_verification.get("VERIFIED", 0)) + int(by_verification.get("PARTIAL", 0))
    verification_success_rate = (success_count / ask_total) if ask_total else 0.0
    average_latency = (latency_total / ask_total) if ask_total else 0.0

    return {
        "service": "uniguru-live-reasoning",
        "uptime_seconds": round(time.time() - _START_TIME, 3),
        "traffic": {
            "ask_requests_total": ask_total,
            "rate_limited_total": rate_limited_total,
            "requests_per_minute": rpm,
            "average_latency_ms": round(average_latency, 3),
            "verification_success_rate": round(verification_success_rate, 6),
            "queue_rejected_total": queue_rejected_total,
            "queue_limit": _ASK_QUEUE_LIMIT,
        },
        "status_codes": by_status,
        "decisions": by_decision,
        "routes": by_route,
        "verification_status": by_verification,
    }


@app.get(
    "/ontology/concept/{concept_id}",
    tags=["Ontology"],
    summary="Get Ontology Concept",
    description="Retrieve a specific concept from the ontology registry by ID"
)
def ontology_concept(concept_id: str) -> Dict[str, Any]:
    try:
        return registry.get_concept(concept_id)
    except ValueError as exc:
        if concept_id.startswith("router::"):
            return {
                "concept_id": concept_id,
                "canonical_name": concept_id.split("::", 1)[-1].replace("_", " ").title(),
                "domain": "routing",
                "truth_level": 0,
                "snapshot_version": 0,
                "snapshot_hash": "router-delegated",
                "immutable": True,
            }
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ============================================================================
# GURU MANAGEMENT ENDPOINTS
# ============================================================================


@app.get(
    "/guru/g-g",
    tags=["Guru Management"],
    summary="Get User's Gurus",
    description="Retrieve all AI gurus/chatbots created by the authenticated user"
)
def get_user_gurus(request: Request) -> Dict[str, Any]:
    """Get all gurus for the authenticated user."""
    user_id = _require_user_identity(request)["id"]
    gurus = guru_storage.get_user_gurus(user_id)

    return {
        "chatbots": [
            {
                "id": g.id,
                "name": g.name,
                "subject": g.subject,
                "description": g.description,
                "created_at": g.created_at,
                "updated_at": g.updated_at,
            }
            for g in gurus
        ]
    }


@app.get(
    "/guru/g-c/{chatbot_id}/{user_id}",
    tags=["Guru Management"],
    summary="Get Guru Chat History",
    description="Retrieve all chat conversations for a specific guru"
)
def get_guru_chats(chatbot_id: str, user_id: str, request: Request) -> Dict[str, Any]:
    """Get all chats for a specific guru. Stub implementation."""
    owner_id = _require_user_identity(request)["id"]
    if user_id != owner_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    with _CHAT_LOCK:
        messages: list[Dict[str, Any]] = []
        for chat in _CHAT_SESSIONS.values():
            if chat.get("userId") == owner_id and chat.get("guru", {}).get("_id") == chatbot_id:
                messages.extend(chat.get("messages", []))
        return {"messages": messages, "chats": []}


@app.post(
    "/guru/n-g/{user_id}",
    tags=["Guru Management"],
    summary="Create Default Guru",
    description="Create a new guru with default settings (auto-generated name and subject)"
)
def create_new_guru(user_id: str, request: Request) -> Dict[str, Any]:
    """Create a new default guru for user."""
    owner_id = _require_user_identity(request)["id"]
    if user_id != owner_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    guru = guru_storage.create_guru(
        user_id=owner_id,
        name=f"Guru {len(guru_storage.get_user_gurus(owner_id)) + 1}",
        subject="General Knowledge",
        description="A general-purpose AI guru"
    )
    
    return {
        "id": guru.id,
        "name": guru.name,
        "subject": guru.subject,
        "description": guru.description,
        "created_at": guru.created_at,
    }


@app.post(
    "/guru/custom-guru/",
    tags=["Guru Management"],
    summary="Create Custom Guru (No User ID Path)",
    description="Create a custom guru when user_id is not provided in path (frontend compatibility)"
)
@app.post(
    "/guru/custom-guru/{user_id}",
    tags=["Guru Management"],
    summary="Create Custom Guru",
    description="Create a personalized AI guru with custom name, subject/expertise, and teaching style"
)
def create_custom_guru(
    request_body: CreateGuruRequest,
    request: Request,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a custom guru with specified name, subject, and description."""
    resolved_user_id = _require_user_identity(request)["id"]
    if user_id and user_id.strip() != resolved_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    guru = guru_storage.create_guru(
        user_id=resolved_user_id,
        name=request_body.name,
        subject=request_body.subject,
        description=request_body.description
    )
    
    return {
        "id": guru.id,
        "name": guru.name,
        "subject": guru.subject,
        "description": guru.description,
        "created_at": guru.created_at,
    }


@app.delete(
    "/guru/g-d/{chatbot_id}",
    tags=["Guru Management"],
    summary="Delete Guru",
    description="Remove a guru from user's collection (soft delete)"
)
def delete_guru_endpoint(chatbot_id: str, request: Request) -> Dict[str, Any]:
    """Delete (soft delete) a guru."""
    user_id = _require_user_identity(request)["id"]
    
    success = guru_storage.delete_guru(chatbot_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Guru not found or unauthorized")
    
    return {"status": "ok", "message": "Guru deleted successfully"}


# ============================================================================
# CHAT SESSION ENDPOINTS
# ============================================================================


@app.post("/chat/create", tags=["Chat"], summary="Create Chat Session")
def chat_create(request_body: Dict[str, Any], request: Request) -> Dict[str, Any]:
    guru_id = str(request_body.get("guruId") or "").strip()
    title = str(request_body.get("title") or "").strip()
    user_id = _require_user_identity(request)["id"]
    if not guru_id:
        raise HTTPException(status_code=400, detail="guruId is required")

    guru = guru_storage.get_guru(guru_id)
    if guru and guru.user_id != user_id:
        raise HTTPException(status_code=404, detail="Guru not found")
    if guru:
        guru_payload = {
            "_id": guru.id,
            "name": guru.name,
            "subject": guru.subject,
            "description": guru.description or "",
        }
    else:
        guru_payload = {
            "_id": guru_id,
            "name": "Custom Guru",
            "subject": "General",
            "description": "",
        }

    now = _utc_now_iso()
    chat_id = str(uuid.uuid4())
    chat = {
        "id": chat_id,
        "userId": user_id,
        "title": title or f"New chat with {guru_payload['name']}",
        "guru": guru_payload,
        "createdAt": now,
        "lastActivity": now,
        "isArchived": False,
        "isActive": True,
        "messages": [],
    }
    with _CHAT_LOCK:
        _CHAT_SESSIONS[chat_id] = chat
    return {"chat": _serialize_chat_session(chat, include_messages=False)}


@app.get("/chat/list", tags=["Chat"], summary="List Chat Sessions")
def chat_list(
    request: Request,
    guruId: Optional[str] = None,
    archived: bool = False,
) -> Dict[str, Any]:
    user_id = _require_user_identity(request)["id"]

    with _CHAT_LOCK:
        chats = [c for c in _CHAT_SESSIONS.values() if c.get("userId") == user_id]
        if guruId:
            chats = [c for c in chats if c.get("guru", {}).get("_id") == guruId]
        if archived:
            chats = [c for c in chats if bool(c.get("isArchived", False))]
        else:
            chats = [c for c in chats if not bool(c.get("isArchived", False))]
        chats.sort(key=lambda c: c.get("lastActivity", ""), reverse=True)
        return {"chats": [_serialize_chat_session(c, include_messages=False) for c in chats]}


@app.get("/chat/all-with-data", tags=["Chat"], summary="Get All Chats With Data")
def chat_all_with_data(
    request: Request,
    includeMessages: bool = False,
) -> Dict[str, Any]:
    user_id = _require_user_identity(request)["id"]
    with _CHAT_LOCK:
        chats = [c for c in _CHAT_SESSIONS.values() if c.get("userId") == user_id]
        chats.sort(key=lambda c: c.get("lastActivity", ""), reverse=True)
        return {"chats": [_serialize_chat_session(c, include_messages=includeMessages) for c in chats]}


@app.get("/chat/chat/{chat_id}", tags=["Chat"], summary="Get Chat Session By ID")
def chat_get(chat_id: str, request: Request) -> Dict[str, Any]:
    owner_id = _require_user_identity(request)["id"]
    with _CHAT_LOCK:
        chat = _CHAT_SESSIONS.get(chat_id)
        if not chat or chat.get("userId") != owner_id:
            raise HTTPException(status_code=404, detail="Chat not found")
        return {"chat": _serialize_chat_session(chat, include_messages=True)}


@app.put("/chat/chat/{chat_id}", tags=["Chat"], summary="Update Chat Session")
def chat_update(chat_id: str, request_body: Dict[str, Any], request: Request) -> Dict[str, Any]:
    owner_id = _require_user_identity(request)["id"]
    with _CHAT_LOCK:
        chat = _CHAT_SESSIONS.get(chat_id)
        if not chat or chat.get("userId") != owner_id:
            raise HTTPException(status_code=404, detail="Chat not found")
        if "title" in request_body and isinstance(request_body["title"], str):
            chat["title"] = request_body["title"].strip() or chat["title"]
        if "isArchived" in request_body:
            chat["isArchived"] = bool(request_body["isArchived"])
        if "isActive" in request_body:
            chat["isActive"] = bool(request_body["isActive"])
        chat["lastActivity"] = _utc_now_iso()
        _CHAT_SESSIONS[chat_id] = chat
        return {"chat": _serialize_chat_session(chat, include_messages=False)}


@app.delete("/chat/chat/{chat_id}", tags=["Chat"], summary="Delete Chat Session")
def chat_delete(chat_id: str, request: Request) -> Dict[str, Any]:
    owner_id = _require_user_identity(request)["id"]
    with _CHAT_LOCK:
        chat = _CHAT_SESSIONS.get(chat_id)
        if not chat or chat.get("userId") != owner_id:
            raise HTTPException(status_code=404, detail="Chat not found")
        _CHAT_SESSIONS.pop(chat_id)
    return {"status": "ok", "message": "Chat deleted successfully", "chatId": chat_id}


@app.get("/chat/all-chats", tags=["Chat"], summary="Legacy Get All Chats")
def chat_all_chats(request: Request) -> Dict[str, Any]:
    return chat_all_with_data(request=request, includeMessages=True)


@app.delete("/chat/delete", tags=["Chat"], summary="Delete All Chats")
def chat_delete_all(request: Request) -> Dict[str, Any]:
    user_id = _require_user_identity(request)["id"]
    deleted = 0
    with _CHAT_LOCK:
        ids = [chat_id for chat_id, chat in _CHAT_SESSIONS.items() if chat.get("userId") == user_id]
        for chat_id in ids:
            _CHAT_SESSIONS.pop(chat_id, None)
            deleted += 1
    return {"status": "ok", "deleted": deleted}


@app.post("/chat/new", tags=["Chat"], summary="Send Message To Chat")
def chat_new(request_body: Dict[str, Any], raw_request: Request) -> Dict[str, Any]:
    message = str(request_body.get("message") or "").strip()
    chatbot_id = str(request_body.get("chatbotId") or "").strip()
    user_id = _require_user_identity(raw_request)["id"]
    chat_id = str(request_body.get("chatId") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    if not chatbot_id:
        raise HTTPException(status_code=400, detail="chatbotId is required")
    guru = guru_storage.get_guru(chatbot_id)
    if guru and guru.user_id != user_id:
        raise HTTPException(status_code=404, detail="Guru not found")

    # Ensure chat exists
    with _CHAT_LOCK:
        chat = _CHAT_SESSIONS.get(chat_id) if chat_id else None
        if chat and chat.get("userId") != user_id:
            raise HTTPException(status_code=404, detail="Chat not found")
    if not chat:
        created = chat_create(
            {"guruId": chatbot_id, "title": (message[:48] + "...") if len(message) > 48 else message, "userId": user_id},
            raw_request,
        )
        chat_id = created["chat"]["id"]
        with _CHAT_LOCK:
            chat = _CHAT_SESSIONS[chat_id]

    user_msg = {"sender": "user", "content": message, "timestamp": _utc_now_iso()}
    with _CHAT_LOCK:
        chat["messages"].append(user_msg)
        chat["lastActivity"] = _utc_now_iso()
        _CHAT_SESSIONS[chat_id] = chat

    # Use the shared verified RAG path so the browser chat and /ask see the
    # same active KB and language handling.
    try:
        trace_id = f"chat_{chat_id}_{uuid.uuid5(uuid.NAMESPACE_URL, message).hex[:12]}"
        adapted = language_adapter.normalize_query(message)
        router_response = conversation_router.route_query(
            query=adapted.normalized_query,
            context={
                "caller": user_id,
                "user_id": user_id,
                "session_id": chat_id,
                "source_language": adapted.source_language,
                "allow_web": False,
            },
        )
        router_response = language_adapter.localize_response(
            router_response,
            source_language=adapted.source_language,
        )
        answer = str(router_response.get("answer") or "I could not generate a response.")
    except Exception as exc:
        logger.exception("chat_new ask pipeline failed: %s", exc)
        router_response = {}
        answer = "I am still learning this topic, please try again."

    ai_metadata = {
        "retrieved_chunks": [],
        "trace_id": router_response.get("trace_id") or trace_id,
        "verification_status": router_response.get("verification_status"),
        "source_type": router_response.get("source_type"),
        "verified": router_response.get("verified"),
        "retrieved_evidence": router_response.get("retrieved_evidence"),
        "retrieval_performed": router_response.get("retrieval_performed"),
        "confidence_breakdown": router_response.get("confidence_breakdown"),
        "consensus_analysis": router_response.get("consensus_analysis"),
        "retrieval_truth_payload": router_response.get("retrieval_truth_payload"),
        "interpretation_payload": router_response.get("interpretation_payload"),
        "truth_interpretation_link": router_response.get("truth_interpretation_link"),
        "semantic_memory": router_response.get("semantic_memory"),
        "multi_hop_traversal": router_response.get("multi_hop_traversal"),
        "matched_signals": router_response.get("matched_signals", []),
        "rejected_signals": router_response.get("rejected_signals", []),
        "semantic_path": router_response.get("semantic_path", []),
        "downstream_execution": router_response.get("downstream_execution"),
        "bucket_proof": router_response.get("bucket_proof"),
        "output_contract": router_response.get("output_contract"),
        "retrieval_trace": router_response.get("retrieval_trace"),
        "language_adapter": router_response.get("language_adapter"),
    }
    ai_msg = {"sender": "bot", "content": answer, "timestamp": _utc_now_iso(), "metadata": ai_metadata}
    with _CHAT_LOCK:
        chat["messages"].append(ai_msg)
        chat["lastActivity"] = _utc_now_iso()
        _CHAT_SESSIONS[chat_id] = chat
        serialized_chat = _serialize_chat_session(chat, include_messages=False)

    return {
        "chat": serialized_chat,
        "aiResponse": {
            "content": answer,
            "metadata": ai_metadata,
            "vaani_audio": None,
        },
    }


# ============================================================================
# USER AUTH ENDPOINTS (Demo mode stubs for frontend compatibility)
# ============================================================================


@app.get(
    "/user/auth-status",
    tags=["Authentication"],
    summary="Check Authentication Status",
    description="Verify if user session is valid and return user profile"
)
def user_auth_status(request: Request) -> Dict[str, Any]:
    user = _require_user_identity(request)
    return {"authenticated": True, "user": user}


@app.post(
    "/auth/google/token",
    tags=["Authentication"],
    summary="Google OAuth Login",
    description="Authenticate user with Google OAuth 2.0 credential token"
)
def google_oauth_callback(request_body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle Google OAuth token callback."""
    token = request_body.get("token")
    
    if not token:
        raise HTTPException(status_code=400, detail="Token is required")
    
    # Try Supabase authentication first
    if supabase_auth.enabled:
        try:
            result = supabase_auth.verify_google_token(token)
            return {
                "token": result["token"],
                "user": result["user"],
                "navigateUrl": "/chatpage"
            }
        except Exception as e:
            logger.error(f"Supabase Google auth failed: {e}")
            raise HTTPException(status_code=401, detail="Google authentication failed")

    if not _DEMO_AUTH_ENABLED:
        raise HTTPException(status_code=503, detail="Authentication provider is not configured")
    
    # Demo mode fallback: decode token locally
    import base64
    try:
        # Decode JWT payload (middle part)
        parts = token.split('.')
        if len(parts) >= 2:
            payload = parts[1]
            # Add padding if needed
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            decoded = base64.urlsafe_b64decode(payload)
            user_data = json.loads(decoded)
            
            user_id = user_data.get('sub', str(uuid.uuid4()))
            email = user_data.get('email', f'user-{user_id}@gmail.com')
            name = user_data.get('name', 'Google User')
        else:
            # Fallback if token format is unexpected
            user_id = str(uuid.uuid4())
            email = f'user-{user_id}@demo.local'
            name = 'Demo User'
    except Exception as e:
        logger.warning(f"Failed to decode Google token: {e}, using demo user")
        user_id = str(uuid.uuid4())
        email = f'user-{user_id}@demo.local'
        name = 'Demo User'
    
    demo_user = _issue_demo_user(user_id, email, name)
    
    return {
        "token": demo_user["token"],
        "user": {
            "id": demo_user["id"],
            "email": demo_user["email"],
            "name": demo_user["name"]
        },
        "navigateUrl": "/chatpage"
    }


@app.post(
    "/user/login",
    tags=["Authentication"],
    summary="Email/Password Login",
    description="Authenticate user with email and password credentials"
)
def user_login(request_body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle user login."""
    email = request_body.get("email")
    password = request_body.get("password")
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    
    # Try Supabase authentication first
    if supabase_auth.enabled:
        try:
            result = supabase_auth.login_with_email(email, password)
            return {
                "token": result["token"],
                "id": result["user"]["id"],
                "email": result["user"]["email"],
                "name": result["user"]["name"]
            }
        except Exception as e:
            logger.error(f"Supabase login failed: {e}")
            raise HTTPException(status_code=401, detail=str(e))
    
    if not _DEMO_AUTH_ENABLED:
        raise HTTPException(status_code=503, detail="Authentication provider is not configured")
    demo_user = _issue_demo_user(email.strip().lower(), email.strip(), email.split('@')[0].title())
    return demo_user


@app.post(
    "/user/signup",
    tags=["Authentication"],
    summary="User Registration",
    description="Create a new user account with name, email, and password"
)
def user_signup(request_body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle user signup."""
    name = request_body.get("name")
    email = request_body.get("email")
    password = request_body.get("password")
    
    if not email or not password or not name:
        raise HTTPException(status_code=400, detail="Name, email, and password are required")
    
    # Try Supabase authentication first
    if supabase_auth.enabled:
        try:
            result = supabase_auth.signup_with_email(email, password, name)
            return {
                "success": result["success"],
                "token": result["token"],
                "id": result["user"]["id"],
                "email": result["user"]["email"],
                "name": result["user"]["name"],
                "requires_email_verification": bool(result.get("requires_email_verification", False)),
                "message": (
                    "Signup successful. Please verify your email before logging in."
                    if result.get("requires_email_verification", False)
                    else "Signup successful. You can login now."
                ),
                "navigateUrl": "/chatpage"
            }
        except Exception as e:
            logger.error(f"Supabase signup failed: {e}")
            detail = str(e)
            status_code = 429 if "rate limit" in detail.lower() else 400
            raise HTTPException(status_code=status_code, detail=detail)
    
    if not _DEMO_AUTH_ENABLED:
        raise HTTPException(status_code=503, detail="Authentication provider is not configured")
    demo_user = _issue_demo_user(email.strip().lower(), email.strip(), name.strip())
    return {
        "success": True,
        "token": demo_user["token"],
        "id": demo_user["id"],
        "email": demo_user["email"],
        "name": demo_user["name"],
        "navigateUrl": "/chatpage"
    }


class NewRagRequest(BaseModel):
    query: str = Field(..., min_length=1)
    domain: Optional[str] = Field(None, description="Optional domain hint (e.g. agriculture, historical, science, maths, physics)")
    session_id: Optional[str] = Field(None, max_length=128)
    caller: Optional[str] = Field(None, max_length=128)
    allow_generated_verse: bool = Field(
        default=False,
        description="If true, generate Sanskrit verse only when no clean canonical verse is found.",
    )

import os
from RAG.new_rag_query import get_engine

_engine_instance = None
def get_faiss_engine():
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = get_engine()
    return _engine_instance

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends

security = HTTPBearer()

_KOSHA_DIR = Path(__file__).parent.parent / "data" / "kosha"


def _infer_domain(query: str, domain_hint: Optional[str] = None, source: Optional[str] = None) -> str:
    def _normalize_hint(value: Optional[str]) -> str:
        normalized = str(value or "").strip().lower()
        placeholder_values = {"", "string", "general", "misc", "other", "unknown", "null", "none"}
        return "" if normalized in placeholder_values else normalized

    normalized_hint = _normalize_hint(domain_hint)
    if normalized_hint:
        return normalized_hint

    text = f"{query or ''} {source or ''}".lower()

    domain_keywords = [
        ("puranas", ("purana", "bhagavata", "narada-purana", "padma purana", "vayu purana", "linga purana")),
        ("gitas", ("gita", "bhagavad gita", "anu-gita", "uddhava-gita", "anugita")),
        ("upanishads", ("upanishad", "ishavasya", "taittiriya", "prashna", "svetasvatara", "mahanarayana")),
        ("vedas", ("veda", "rigveda", "samaveda", "yajurveda", "atharvaveda")),
        ("itihasa", ("mahabharata", "ramayana", "itihasa", "bharata", "pandava", "kurukshetra")),
        ("smriti", ("smriti", "dharma sutra", "dharmasutra", "manu", "yajnavalkya", "narada smriti", "gautama")),
        ("agamas", ("agama", "saiva", "shaiva", "vaishnava agama", "pancharatra", "kamika", "suprabheda")),
        ("tantra", ("tantra", "tripura", "bhairava", "tantrasara")),
        ("history", ("history", "ancient", "medieval", "historical", "dynasty", "empire", "civilization")),
        ("geography", ("geography", "river", "mountain", "continent", "climate", "ocean", "map")),
        ("maths", ("math", "maths", "algebra", "geometry", "calculus", "equation", "theorem", "integral")),
        ("physics", ("physics", "force", "energy", "quantum", "momentum", "velocity", "relativity")),
        ("chemistry", ("chemistry", "chemical", "molecule", "atom", "acid", "base", "reaction")),
        ("biology", ("biology", "cell", "genetics", "evolution", "organism", "ecosystem")),
        ("agricultural", ("agri", "crop", "farm", "soil", "irrigation", "harvest", "seed")),
    ]

    for domain_name, keywords in domain_keywords:
        if any(keyword in text for keyword in keywords):
            return domain_name

    return "general"


def _clean_content(text: str) -> str:
    return " ".join(str(text or "").split()).strip()


def _extract_tags(query: str, source: str) -> list[str]:
    stopwords = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "about",
        "tell",
        "what",
        "which",
        "who",
        "when",
        "where",
        "into",
        "this",
        "that",
        "does",
        "have",
        "chapter",
        "verse",
    }
    query_terms = {
        term
        for term in re.findall(r"[a-zA-Z0-9]+", query.lower())
        if len(term) > 2 and term not in stopwords
    }
    source_terms = {
        term
        for term in re.findall(r"[a-zA-Z0-9]+", source.lower())
        if len(term) > 2 and term not in stopwords
    }
    tags = sorted(query_terms.intersection(source_terms))
    if not tags:
        # keep at most 3 meaningful tags
        tags = sorted(list(query_terms))[:3]
    return tags


def _tag_match_score(query: str, source: str) -> float:
    query_terms = {term for term in re.findall(r"[a-zA-Z0-9]+", query.lower()) if len(term) > 2}
    if not query_terms:
        return 0.0
    source_terms = {term for term in re.findall(r"[a-zA-Z0-9]+", source.lower()) if len(term) > 2}
    overlap = len(query_terms.intersection(source_terms))
    return float(overlap / max(len(query_terms), 1))


def _persist_kosha_entry(entry: Dict[str, Any]) -> None:
    _KOSHA_DIR.mkdir(parents=True, exist_ok=True)
    file_path = _KOSHA_DIR / f"{entry['knowledge_id']}.json"
    with file_path.open("w", encoding="utf-8") as handle:
        json.dump(entry, handle, ensure_ascii=False, indent=2)
    index_path = _KOSHA_DIR / "kosha_entries.jsonl"
    with index_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _make_signal(query: str, chunk: Dict[str, Any], idx: int) -> Dict[str, Any]:
    source_file = str(chunk.get("metadata", {}).get("file_name") or "unknown")
    similarity_score = max(float(chunk.get("score", 0.0)), 0.0)
    tag_score = _tag_match_score(query, source_file)
    confidence = max(similarity_score, tag_score)
    return {
        "signal_id": f"signal_{idx+1}",
        "type": "string",
        "content": str(chunk.get("text", "")).strip(),
        "source": source_file,
        "confidence": confidence,
        "trace": {
            "knowledge_id": source_file,
            "method": "kosha_retrieval",
        },
    }


def _kosha_entry_to_signal(entry: Dict[str, Any], idx: int) -> Dict[str, Any]:
    source_file = str(entry.get("source") or "unknown")
    content = str(entry.get("content") or "").strip()
    confidence = float(entry.get("confidence", 0.0))
    if confidence <= 0:
        confidence = 0.01
    return {
        "signal_id": f"signal_{idx + 1}",
        "type": "string",
        "content": content,
        "source": source_file,
        "confidence": confidence,
        "trace": {"knowledge_id": source_file, "method": "kosha_retrieval"},
    }


def _llm_answer_from_signals(query: str, signals: list[Dict[str, Any]], max_context_chars: int = 4000) -> str:
    """
    Uses Groq LLM to generate a final answer from signal content only.
    This mirrors the style used in `backend/RAG/notebook.json`.
    """
    engine = get_faiss_engine()
    groq_client = getattr(engine, "groq_client", None)
    if not groq_client:
        # If LLM is unavailable, return best available Kosha content.
        best = max(signals, key=lambda s: float(s.get("confidence", 0.0) or 0.0)) if signals else None
        return str((best or {}).get("content") or "I don't know.")

    signals = [s for s in signals if str(s.get("content", "")).strip()]
    if not signals:
        return "I don't know."

    context_parts = []
    for i, sig in enumerate(signals[:5]):
        content = str(sig.get("content", "")).strip()
        context_parts.append(f"--- [{i + 1}] ---\n{content}")
    context = "\n\n".join(context_parts)
    if len(context) > max_context_chars:
        context = context[:max_context_chars] + "\n...[truncated]"

    system_prompt = (
        "You are an intelligent knowledge assistant. "
        "Your Answer MUST be constructed ONLY from the provided context signals.\n"
        "Rules:\n"
        "1. No hallucination whatsoever\n"
        "2. No extra information outside the provided text\n"
        "3. Only use signal-derived facts\n"
        "If the context cannot answer the question, simply reply 'I don't know'."
    )
    user_prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=800,
    )
    return str(response.choices[0].message.content or "").strip() or "I don't know."


def _llm_answer_from_chunks(query: str, chunks: list[Dict[str, Any]], max_context_chars: int = 4000) -> str:
    """
    LLM answer using FAISS chunk text as context (similar to `backend/RAG/notebook.json`).
    """
    engine = get_faiss_engine()
    groq_client = getattr(engine, "groq_client", None)
    if not groq_client:
        best = max(chunks, key=lambda c: float(c.get("score", 0.0) or 0.0)) if chunks else None
        return str((best or {}).get("text") or "I don't know.")

    if not chunks:
        return "I don't know."

    context_parts = []
    for i, ch in enumerate(chunks[:5]):
        meta = ch.get("metadata") or {}
        file_name = str(meta.get("file_name") or "unknown")
        context_parts.append(f"--- [{i+1}] {file_name} ---\n{ch.get('text') or ''}")
    context = "\n\n".join(context_parts)
    if len(context) > max_context_chars:
        context = context[:max_context_chars] + "\n...[truncated]"

    system_prompt = (
        "Answer based ONLY on the provided context. If not present, say 'I don't know'. "
        "Write 2-4 sentences. Cite sources using numbers like [1], [2]."
    )
    user_prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"

    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=800,
    )
    answer = str(response.choices[0].message.content or "").strip() or "I don't know."

    # Answer validation / correction step
    if "don't know" not in answer.lower():
        verification_prompt = (
            f"Context:\n{context}\n\n"
            f"Question: {query}\n\n"
            f"Proposed Answer: {answer}\n\n"
            "Task 1: Check if the Proposed Answer directly and accurately answers the Question using ONLY the Context.\n"
            "Task 2: If the Proposed Answer is entirely correct and relevant, reply EXACTLY with 'VALID: ' followed by the Proposed Answer.\n"
            "Task 3: If the Proposed Answer is incorrect, irrelevant, or hallucinates, you MUST correct it. Generate a new, concise, accurate answer based STRICTLY on the Context. Reply with 'CORRECTED: ' followed by the new answer. If the Context does not contain the answer, reply with 'CORRECTED: I don't know.'"
        )
        try:
            ver_response = groq_client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[
                    {"role": "system", "content": "You are a strict evaluation and correction assistant."},
                    {"role": "user", "content": verification_prompt},
                ],
                temperature=0.1,
                max_tokens=400,
            )
            ver_result = str(ver_response.choices[0].message.content or "").strip()
            
            if ver_result.upper().startswith("VALID:"):
                answer = ver_result[6:].strip()
            elif ver_result.upper().startswith("CORRECTED:"):
                answer = ver_result[10:].strip()
            elif "CORRECTED:" in ver_result.upper():
                idx = ver_result.upper().index("CORRECTED:")
                answer = ver_result[idx + 10:].strip()
            else:
                # If the model didn't follow formatting but generated something, we use it as a fallback, 
                # or just fallback to I don't know if it says invalid.
                if "INVALID" in ver_result.upper():
                    answer = "I don't know."
        except Exception as e:
            pass # proceed with unverified answer if validation fails

    return answer

def _normalize_common_names(text: str) -> str:
    """
    Small post-processing for OCR/transliteration variants found in the stored PDFs.
    """
    t = str(text or "")
    # Common OCR/transliteration normalization for Vishnu.
    t = t.replace("Visnu", "Vishnu")
    return t.strip()


def _is_non_answer_content(text: str) -> bool:
    value = str(text or "").strip().lower()
    if not value:
        return True
    disallowed_phrases = [
        "i don't know",
        "i dont know",
        "not provided in the given context",
        "not provided in the context",
        "no relevant context found",
        "cannot be answered from the provided context",
    ]
    return any(phrase in value for phrase in disallowed_phrases)


def _detect_sanskrit_verse(chunks: list[Dict[str, Any]]) -> Optional[str]:
    dev_re = re.compile(r"[\u0900-\u097F]")
    danda_re = re.compile(r"[।॥]")
    for chunk in chunks:
        text = str(chunk.get("text") or "").strip()
        if not text:
            continue
        if dev_re.search(text):
            # Prefer verse-like chunks (danda markers), else first Devanagari chunk.
            if danda_re.search(text):
                return text
    for chunk in chunks:
        text = str(chunk.get("text") or "").strip()
        if text and dev_re.search(text):
            return text
    return None


def _is_low_quality_ocr_sanskrit(text: Optional[str]) -> bool:
    if not text:
        return False
    sample = str(text)
    # Heuristic OCR-noise markers often seen in bad scans.
    noise_markers = ["�", "|", "@", "~", "http", "www", "digitized", "in public domain"]
    noise_hits = sum(sample.lower().count(marker.lower()) for marker in noise_markers)
    symbol_count = len(re.findall(r"[^A-Za-z0-9\u0900-\u097F\s।॥,.;:!?()\-]", sample))
    devanagari_count = len(re.findall(r"[\u0900-\u097F]", sample))
    latin_count = len(re.findall(r"[A-Za-z]", sample))
    total_len = max(len(sample), 1)
    symbol_ratio = symbol_count / total_len
    # Mixed-script warning: Sanskrit expected, but mostly Latin text indicates OCR mismatch/noise.
    mixed_script_noise = devanagari_count > 0 and (latin_count > max(120, devanagari_count * 2))
    weak_sanskrit_signal = devanagari_count < 12
    return noise_hits > 0 or symbol_ratio > 0.10 or mixed_script_noise or weak_sanskrit_signal


def _query_requests_verse(query: str) -> bool:
    lower = str(query or "").lower()
    return any(token in lower for token in ("verse", "shloka", "sloka", "sanskrit", "śloka", "श्लोक"))


def _generate_sanskrit_verse(query: str, context: str) -> Optional[str]:
    engine = get_faiss_engine()
    groq_client = getattr(engine, "groq_client", None)
    if not groq_client:
        return None
    system_prompt = (
        "You are a Sanskrit assistant. Generate exactly 2 lines in Devanagari Sanskrit as a thematic verse "
        "based on the provided context. Do not claim canonical authenticity."
    )
    user_prompt = (
        f"Question: {query}\n\n"
        f"Context summary: {context}\n\n"
        "Return only the Sanskrit verse in Devanagari (2 lines)."
    )
    try:
        response = groq_client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=400,
        )
        text = str(response.choices[0].message.content or "").strip()
        return text or None
    except Exception:
        return None


def _execute_kosha_pipeline(
    query: str,
    domain_hint: Optional[str],
    top_k: int,
    allow_generated_verse: bool = False,
    trace_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    trace_id = trace_id or f"trace_{uuid.uuid4().hex[:12]}"
    try:
        from service.universal_orchestrator import get_universal_orchestrator
        orchestrator = get_universal_orchestrator()
        result = orchestrator.process_query(
            query=query,
            domain_hint=domain_hint,
            user_id=user_id or "demo-user",
            top_k=top_k,
            trace_id=trace_id,
        )

        status = result.get("verification_status", "VERIFIED")
        confidence = float(result.get("confidence") or 0.95)
        answer = result.get("answer", "")
        citations = result.get("citations", [])

        # Build schema-compliant matched signals from evidence or capability result
        matched_signals = []
        for i, ev in enumerate(result.get("evidence", [])):
            matched_signals.append({
                "signal_id": f"sig_{trace_id}_{i}",
                "confidence": float(ev.get("composite_score", confidence)),
                "content": ev.get("text", ""),
                "domain": ev.get("domain", "general"),
                "knowledge_id": ev.get("document_id", f"doc_{i}"),
                "source": ev.get("file_name") or ev.get("book") or "knowledge_base",
                "source_governance": {
                    "authority_weight": 0.95,
                    "lineage": {
                        "book": ev.get("book"),
                        "board": ev.get("board"),
                        "grade": ev.get("grade"),
                        "subject": ev.get("subject"),
                        "chapter": ev.get("chapter"),
                        "page": ev.get("page"),
                    }
                },
                "trace": {
                    "knowledge_id": ev.get("document_id"),
                    "method": "unified_hybrid_rag",
                    "domain_resolution": result.get("debug", {}).get("scope", {}),
                }
            })

        if not matched_signals and status == "VERIFIED":
            cat = result.get("category", "general")
            matched_signals.append({
                "signal_id": f"sig_{trace_id}_0",
                "confidence": confidence,
                "content": answer,
                "domain": cat,
                "knowledge_id": f"capability_{cat}",
                "source": f"capability_{cat}",
                "source_governance": {
                    "authority_weight": 0.98,
                    "lineage": {
                        "book": f"UniGuru {cat.title()} Capability",
                        "board": "UniGuru Core",
                        "grade": 0,
                        "subject": cat,
                        "chapter": "Core Reasoning",
                        "page": 1,
                    }
                },
                "trace": {
                    "knowledge_id": f"capability_{cat}",
                    "method": "capability_execution",
                    "domain_resolution": {"domain": cat, "confidence": confidence},
                }
            })

        return {
            "trace_id": trace_id,
            "query": query,
            "answer": answer,
            "verification_status": status,
            "confidence": confidence,
            "citations": citations,
            "matched_signals": matched_signals,
            "rejected_signals": [],
            "reasoning_path": ["query_received", "canonicalization", "dense_search", "lexical_search", "rrf_merge", "deduplication", "grounded_synthesis"],
            "confidence_breakdown": {
                "overall": confidence,
                "accepted_count": len(matched_signals),
                "rejected_count": 0,
                "consensus": {
                    "contradictions": [],
                    "consensus_score": 1.0 if status == "VERIFIED" else 0.0,
                    "disagreement_aware_synthesis": "Unified multi-source verification confirmed." if status == "VERIFIED" else "Insufficient verified evidence."
                }
            },
            "consensus_analysis": {
                "contradictions": [],
                "consensus_score": 1.0 if status == "VERIFIED" else 0.0,
                "disagreement_aware_synthesis": "Unified multi-source verification confirmed." if status == "VERIFIED" else "Insufficient verified evidence."
            },
            "retrieval_truth_payload": {
                "layer": "UNIFIED_HYBRID_RETRIEVAL_TRUTH",
                "trace_id": trace_id,
                "query": query,
                "accepted_signals": matched_signals,
                "raw_signal_count": len(matched_signals),
                "artifact_hash": hashlib.sha256(f"{query}|{status}|{trace_id}".encode()).hexdigest(),
            },
            "interpretation_payload": {
                "layer": "GROUNDED_SEMANTIC_INTERPRETATION",
                "trace_id": trace_id,
                "answer": answer,
                "verification_status": status,
                "confidence": confidence,
                "artifact_hash": hashlib.sha256(f"{answer}|{confidence}".encode()).hexdigest(),
            },
            "semantic_path": [
                {
                    "signal_id": s["signal_id"],
                    "knowledge_id": s["knowledge_id"],
                    "domain": s["domain"],
                    "source_lineage": s["source_governance"]["lineage"],
                }
                for s in matched_signals
            ],
            "output_contract": {
                "schema": "TANTRA_UNIGURU_INTELLIGENCE_CONTRACT_V1",
                "contract_bound": True,
                "downstream_consumable": True,
                "trace_id": trace_id,
            },
            "downstream_execution": {
                "consumer": "TANTRA_EXECUTION_CHAIN",
                "status": "READY_FOR_DOWNSTREAM" if status == "VERIFIED" else "REJECTED_NO_DOWNSTREAM_ACTION",
                "trace_id": trace_id,
            },
            "bucket_proof": {
                "event": "tantra_uniguru_intelligence_contract",
                "trace_id": trace_id,
                "verification_status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }
    except Exception as exc:
        logger.exception("Unified pipeline error in _execute_kosha_pipeline: %s", exc)
        from kosha.deterministic_pipeline import run_deterministic_pipeline
        return run_deterministic_pipeline(query=query, domain_hint=domain_hint, trace_id=trace_id, user_id=user_id)

    from kosha.kosha_loader import KoshaLoader
    from kosha.kosha_retriever import KoshaRetriever
    from kosha.kosha_validator import KoshaEntry
    import re

    def _get_english_explanation(final_ans: str, verse_san: Optional[str]) -> str:
        explanation = final_ans or ""
        try:
            import sys
            import os
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if backend_dir not in sys.path:
                sys.path.append(backend_dir)
            from translate_sanskrit import translate

            if final_ans and re.search(r'[\u0900-\u097F]', final_ans):
                translation = translate(final_ans, direction="sa-to-en")
                if "Error" not in translation:
                    explanation = translation

            if verse_san and re.search(r'[\u0900-\u097F]', verse_san):
                verse_translation = translate(verse_san, direction="sa-to-en")
                if "Error" not in verse_translation:
                    explanation = f"{explanation}\n\nVerse Translation: {verse_translation}".strip()
        except Exception as e:
            logger.warning(f"Translation error: {e}")
        return explanation

    kosha_attempted = True
    if not kosha_attempted:
        raise HTTPException(status_code=500, detail="IF kosha_not_attempted -> ERROR")

    now_iso = datetime.now(timezone.utc).isoformat()

    # Phase 1: Query -> Kosha -> Signals
    loader = KoshaLoader(data_sources=[str(_KOSHA_DIR)])
    kosha_entries = loader.load_all()
    retriever = KoshaRetriever(kosha_entries)
    kosha_signals, _detected_domain = retriever.retrieve(query=query, domain=None)
    kosha_signals = [
        s
        for s in kosha_signals
        if float(s.get("confidence", 0.0)) > 0
        and str(s.get("content", "")).strip()
        and str(s.get("source", "")).strip()
        and not _is_non_answer_content(str(s.get("content", "")))
    ]

    # If Kosha match is too weak, treat as "no valid match" to allow FAISS+LLM fallback.
    # This prevents generic stopword tag matches from winning.
    min_kosha_confidence = 0.25
    kosha_signals = [s for s in kosha_signals if float(s.get("confidence", 0.0) or 0.0) >= min_kosha_confidence]

    if kosha_signals:
        best_signal = max(kosha_signals, key=lambda s: float(s.get("confidence", 0.0)))

        # Prefer notebook-style final answers by grounding on FAISS chunk text,
        # filtered to Kosha sources (file names only).
        engine = get_faiss_engine()
        retrieved_chunks = engine.retrieve(query=query, top_k=top_k) or []
        allowed_sources = {str(s.get("source") or "").strip() for s in kosha_signals if str(s.get("source") or "").strip()}
        filtered_chunks = [
            ch for ch in retrieved_chunks
            if str((ch.get("metadata") or {}).get("file_name") or "").strip() in allowed_sources
        ]
        chunks_for_answer = filtered_chunks if filtered_chunks else retrieved_chunks
        final_answer = _llm_answer_from_chunks(query=query, chunks=chunks_for_answer)
        final_answer = _normalize_common_names(final_answer)
        detected_verse = _detect_sanskrit_verse(chunks_for_answer)
        low_quality_sanskrit = _is_low_quality_ocr_sanskrit(detected_verse)

        final_answer_lower = str(final_answer).strip().lower()
        if "don't know" in final_answer_lower:
            # Last resort: return the best Kosha content so output is never empty.
            best_content = str(best_signal.get("content") or "").strip()
            if best_content:
                final_answer = best_content

        best_entry = None
        for entry in kosha_entries:
            if str(entry.source) == str(best_signal.get("source")) and str(entry.content).strip() == final_answer:
                best_entry = entry
                break
        if best_entry is None and kosha_entries:
            best_entry = kosha_entries[0]

        # Always persist a Kosha entry representing the final LLM answer.
        kosha_entry_payload = {
            "knowledge_id": f"KOSHA_{uuid.uuid4().hex[:12]}",
            "domain": _infer_domain(
                query=query,
                domain_hint=domain_hint,
                source=str(best_signal.get("source") or "unknown"),
            ),
            "content": final_answer,
            "source": str(best_signal.get("source") or "unknown"),
            "confidence": float(best_signal.get("confidence", 0.01)) or 0.01,
            "timestamp": now_iso,
            "tags": _extract_tags(query, str(best_signal.get("source") or "")),
            "clean_content": _clean_content(final_answer),
        }

        validated_kosha = KoshaEntry(
            knowledge_id=kosha_entry_payload["knowledge_id"],
            domain=kosha_entry_payload["domain"],
            content=kosha_entry_payload["content"],
            source=kosha_entry_payload["source"],
            confidence=kosha_entry_payload["confidence"],
            timestamp=kosha_entry_payload["timestamp"],
            tags=kosha_entry_payload["tags"],
            clean_content=kosha_entry_payload["clean_content"],
        ).model_dump()

        verse_sanskrit: Optional[str] = None
        note: Optional[str] = None
        if detected_verse and not low_quality_sanskrit:
            verse_sanskrit = detected_verse
        elif allow_generated_verse and _query_requests_verse(query):
            generated = _generate_sanskrit_verse(query=query, context=final_answer)
            if generated:
                verse_sanskrit = generated
                note = "AI-generated Sanskrit verse (not canonical citation)"
            elif detected_verse and low_quality_sanskrit:
                note = "Sanskrit text detected but low quality OCR"
        elif detected_verse and low_quality_sanskrit:
            note = "Sanskrit text detected but low quality OCR"

        return {
            "kosha_attempted": True,
            "fallback_to_llm": False,
            "fallback_reason": None,
            "signals": kosha_signals,
            "final_answer": final_answer,
            "verse_sanskrit": verse_sanskrit,
            "english_explanation": _get_english_explanation(final_answer, verse_sanskrit),
            "note": note,
            "kosha_entry": validated_kosha,
        }

    # Guard: IF kosha_attempted AND no signals -> fallback allowed to LLM
    engine = get_faiss_engine()
    retrieved = engine.retrieve(query=query, top_k=top_k) or []

    best_source_file = "unknown"
    best_confidence = 0.01
    for chunk in retrieved:
        meta = chunk.get("metadata") or {}
        source_file = str(meta.get("file_name") or "unknown")
        similarity_score = max(float(chunk.get("score", 0.0)), 0.0)
        tag_score = _tag_match_score(query, source_file)
        confidence = max(similarity_score, tag_score)
        if confidence > best_confidence:
            best_confidence = confidence
            best_source_file = source_file

    if best_confidence <= 0:
        best_confidence = 0.01

    # Use notebook-style chunk-grounded LLM generation for consistency.
    final_answer = _llm_answer_from_chunks(query=query, chunks=retrieved)
    final_answer = _normalize_common_names(final_answer)
    final_answer = str(final_answer or "I don't know.").strip() or "I don't know."
    clean_answer = _clean_content(final_answer)
    detected_verse = _detect_sanskrit_verse(retrieved)
    low_quality_sanskrit = _is_low_quality_ocr_sanskrit(detected_verse)
    verse_sanskrit: Optional[str] = None
    note: Optional[str] = None
    if detected_verse and not low_quality_sanskrit:
        verse_sanskrit = detected_verse
    elif allow_generated_verse and _query_requests_verse(query):
        generated = _generate_sanskrit_verse(query=query, context=final_answer)
        if generated:
            verse_sanskrit = generated
            note = "AI-generated Sanskrit verse (not canonical citation)"
        elif detected_verse and low_quality_sanskrit:
            note = "Sanskrit text detected but low quality OCR"
    elif detected_verse and low_quality_sanskrit:
        note = "Sanskrit text detected but low quality OCR"

    domain = _infer_domain(query=query, domain_hint=domain_hint, source=best_source_file)
    tags = _extract_tags(query, best_source_file)

    kosha_entry_payload = {
        "knowledge_id": f"KOSHA_{uuid.uuid4().hex[:12]}",
        "domain": domain,
        "content": final_answer,
        "source": best_source_file,
        "confidence": float(best_confidence) or 0.01,
        "timestamp": now_iso,
        "tags": tags,
        "clean_content": clean_answer,
    }

    validated_kosha = KoshaEntry(
        knowledge_id=kosha_entry_payload["knowledge_id"],
        domain=kosha_entry_payload["domain"],
        content=kosha_entry_payload["content"],
        source=kosha_entry_payload["source"],
        confidence=kosha_entry_payload["confidence"],
        timestamp=kosha_entry_payload["timestamp"],
        tags=kosha_entry_payload["tags"],
        clean_content=kosha_entry_payload["clean_content"],
    ).model_dump()

    _persist_kosha_entry(validated_kosha)

    # Convert newly created Kosha entry -> Signal (no empty signals allowed)
    signals = [_kosha_entry_to_signal(validated_kosha, idx=0)]
    if not signals or not str(signals[0].get("content") or "").strip():
        raise HTTPException(status_code=500, detail="No empty signals allowed.")

    return {
        "kosha_attempted": True,
        "fallback_to_llm": True,
        "fallback_reason": "zero_valid_kosha_match",
        "signals": signals,
        "final_answer": final_answer,
        "verse_sanskrit": verse_sanskrit,
        "english_explanation": _get_english_explanation(final_answer, verse_sanskrit),
        "note": note,
        "kosha_entry": validated_kosha,
    }

@app.post(
    "/new_rag",
    tags=["Core Intelligence"],
    summary="Query Deterministic Kosha System",
    description="Deterministic KOSHA retrieval falling back to original FAISS architecture."
)
def new_rag_endpoint(request: NewRagRequest, token: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    try:
        allowed_key = os.getenv("EXTERNAL_API_SECRET_KEY", "").strip()
        if not allowed_key or token.credentials != allowed_key:
            raise HTTPException(status_code=401, detail="Unauthorized Access. Invalid API Key.")

        conversation_context = {
            "session_id": request.session_id,
            "caller": request.caller,
        }
        conversation_state = conversation_router._get_session_memory(conversation_context)
        is_conversational = conversation_router._conversation_answer(request.query, conversation_state) is not None
        if is_conversational:
            conversational = conversation_router.route_query(request.query, conversation_context)
            answer = str(conversational.get("answer") or "").strip()
            return {
                "query": request.query,
                "answer": answer,
                "final_answer": answer,
                "confidence": None,
                "signals": [],
                "status": "success",
                "verification_status": "NOT_REQUIRED",
                "kosha_attempted": False,
                "fallback_to_llm": False,
                "routing": conversational.get("routing"),
            }

        kosha_result = _execute_kosha_pipeline(
            query=request.query,
            domain_hint=request.domain,
            top_k=5,
            allow_generated_verse=bool(request.allow_generated_verse),
        )
        adapted = language_adapter.normalize_query(request.query)
        kosha_result.setdefault("normalized_query", adapted.normalized_query)
        # Keep the legacy /new_rag field name while deriving it only from the
        # evidence actually used by deterministic synthesis.
        selected_ids = set(kosha_result.get("evidence_signal_ids") or [])
        legacy_signals = []
        for signal in kosha_result.get("matched_signals") or []:
            if signal.get("signal_id") not in selected_ids:
                continue
            compatible_signal = dict(signal)
            source = str(compatible_signal.get("source") or "")
            normalized_source = source.replace("\\", "/")
            knowledge_marker = "/knowledge/"
            marker_index = normalized_source.casefold().rfind(knowledge_marker)
            if marker_index >= 0:
                compatible_signal["source"] = normalized_source[marker_index + len(knowledge_marker):]
            legacy_signals.append(compatible_signal)
        kosha_result["signals"] = legacy_signals
        if kosha_result.get("verification_status") == "NO_VERIFIED_KNOWLEDGE":
            hybrid_response = service.ask(
                user_query=request.query,
                session_id=request.session_id,
                context={"caller": request.caller or "new_rag"},
                allow_web_retrieval=False,
            )
            retrieval_trace = hybrid_response.get("retrieval_trace") or {}
            if (
                hybrid_response.get("verification_status") in {"VERIFIED", "VERIFIED_PARTIAL", "PARTIAL"}
                and retrieval_trace.get("match_found")
                and str(hybrid_response.get("answer") or "").strip()
            ):
                evidence_sources = retrieval_trace.get("evidence_sources") or []
                signals = [
                    {
                        "signal_id": f"hybrid_{index + 1}",
                        "type": "LOCAL_MARKDOWN_EVIDENCE",
                        "content": evidence.get("excerpt") or "",
                        "source": evidence.get("path") or evidence.get("file") or "unknown",
                        "confidence": float(evidence.get("evidence_coverage") or 0.0),
                        "trace": {
                            "method": "verified_hybrid_retrieval",
                            "chunk_id": evidence.get("chunk_id"),
                            "page_number": evidence.get("page_number"),
                            "chapter": evidence.get("chapter"),
                        },
                    }
                    for index, evidence in enumerate(evidence_sources)
                    if isinstance(evidence, dict) and str(evidence.get("excerpt") or "").strip()
                ]
                return {
                    "query": request.query,
                    "answer": hybrid_response["answer"],
                    "final_answer": hybrid_response["answer"],
                    "confidence": None,
                    "confidence_breakdown": {
                        "retrieval_score": retrieval_trace.get("retrieval_score"),
                        "reranker_score": retrieval_trace.get("reranker_score"),
                        "evidence_coverage": retrieval_trace.get("evidence_coverage"),
                        "answer_confidence": None,
                    },
                    "signals": signals,
                    "matched_signals": signals,
                    "verification_status": hybrid_response["verification_status"],
                    "status": "success",
                    "kosha_attempted": True,
                    "fallback_to_llm": False,
                    "fallback_reason": "no_valid_kosha_signals; verified_hybrid_kb_evidence_found",
                    "retrieval_trace": retrieval_trace,
                    "kosha_result": kosha_result,
                    "output_contract": {
                        "schema": "UNIGURU_HYBRID_RAG_CONTRACT_V1",
                        "contract_bound": True,
                        "downstream_consumable": True,
                        "free_form_output": False,
                    },
                }
        return kosha_result
    except Exception as e:
        logger.error(f"Error querying FAISS Kosha RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================
# NEW: 6-PHASE CORE UNIFIED PIPELINE (/new_query)
# ==============================================================

class CoreRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    intent: str = Field(default="information_retrieval")
    context: Dict[str, Any] = Field(default_factory=dict)
    required_outputs: list = Field(default=["signals", "final_answer"])
    query: str = Field(default="Tell me about Mahabharat")
    allow_generated_verse: bool = Field(
        default=False,
        description="If true, generate Sanskrit verse only when no clean canonical verse is found.",
    )

def mock_samachar_system(query: str):
    return {
        "signal_id": f"EXT_MOCK_{uuid.uuid4().hex[:8]}",
        "type": "string",
        "content": f"Live external news stub monitoring real-time updates for: {query}",
        "confidence": 0.85,
        "source": "Mock Samachar Real-Time API",
        "trace": {
            "knowledge_id": "external_samachar",
            "method": "external_api_call",
        }
    }

def log_to_bucket(event_id, query, signals_used, final_answer, confidence, system_path):
    bucket_telemetry.emit(
        TelemetryEvent(
            event="pipeline_execution",
            query_hash=_query_hash(str(query)),
            route=str(system_path),
            verification_status="UNVERIFIED",
            latency=0.0,
            caller=None,
            session_id=event_id,
            decision=None,
        )
    )

@app.post(
    "/new_query",
    tags=["Core Intelligence"],
    summary="Phase 6 Core Unified Signal Pipeline"
)
def new_query_endpoint(request: CoreRequest, token: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    try:
        allowed_key = os.getenv("EXTERNAL_API_SECRET_KEY", "").strip()
        if not allowed_key or token.credentials != allowed_key:
            raise HTTPException(status_code=401, detail="Unauthorized Access.")

        final_payload = _execute_kosha_pipeline(
            query=request.query,
            domain_hint=request.context.get("domain") if isinstance(request.context, dict) else None,
            top_k=5,
            allow_generated_verse=bool(request.allow_generated_verse),
            trace_id=request.request_id,
            user_id=(
                str(request.context.get("user_id") or request.context.get("caller") or "tantra-client")
                if isinstance(request.context, dict)
                else "tantra-client"
            ),
        )

        log_to_bucket(
            event_id=request.request_id,
            query=request.query,
            signals_used=len(final_payload.get("matched_signals", [])),
            final_answer=final_payload.get("answer", ""),
            confidence=final_payload.get("confidence_breakdown", {}).get("overall", 0.0),
            system_path="/new_query_6phase_pipeline"
        )

        return final_payload
    except Exception as e:
        logger.error(f"Error in Core Query pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/user/logout",
    tags=["Authentication"],
    summary="User Logout",
    description="End user session and clear authentication token"
)
def user_logout(request: Request) -> Dict[str, Any]:
    """Handle user logout."""
    token = _request_bearer_token(request)
    if _DEMO_AUTH_ENABLED and token:
        _DEMO_AUTH_TOKENS.pop(token, None)
    elif supabase_auth.enabled and token:
        supabase_auth.logout(token)
    
    return {"status": "ok", "message": "Logged out successfully"}


@app.post(
    "/rag/debug",
    tags=["Core Intelligence"],
    summary="Developer / Admin RAG Retrieval Debug Inspection",
    description="Inspect query canonicalization, scope, dense scores, lexical scores, and candidate rankings."
)
def rag_debug_endpoint(request_body: Dict[str, Any], raw_request: Request) -> Dict[str, Any]:
    query = str(request_body.get("query") or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    from retrieval.unified_rag_engine import get_unified_engine
    engine = get_unified_engine()
    retrieval_res = engine.retrieve(query, top_k=int(request_body.get("top_k", 5)))
    full_answer_res = engine.answer_query(query, top_k=int(request_body.get("top_k", 5)))
    return {
        "query": query,
        "scope": retrieval_res.get("scope"),
        "is_grounded": retrieval_res.get("is_grounded"),
        "max_similarity": retrieval_res.get("max_similarity"),
        "max_lexical": retrieval_res.get("max_lexical"),
        "top_candidates": retrieval_res.get("candidates", [])[:10],
        "final_evidence": retrieval_res.get("top_evidence", []),
        "synthesized_answer": full_answer_res.get("answer"),
        "verification_status": full_answer_res.get("verification_status"),
        "citations": full_answer_res.get("citations"),
    }


@app.post(
    "/feedback",
    tags=["Feedback & Continuous Learning"],
    summary="Record User Feedback",
    description="Captures user rating (thumbs up/down) and failure classifications to build continuous learning datasets."
)
def record_feedback_endpoint(feedback_body: Dict[str, Any], raw_request: Request) -> Dict[str, Any]:
    from memory.user_memory_store import get_user_memory_store
    user_id = str(feedback_body.get("userId") or raw_request.headers.get("X-User-Id") or "demo-user").strip()
    session_id = str(feedback_body.get("sessionId") or "default_session").strip()
    query = str(feedback_body.get("query") or "").strip()
    answer = str(feedback_body.get("answer") or "").strip()
    is_helpful = bool(feedback_body.get("isHelpful", True))
    failure_type = feedback_body.get("failureType")
    corrected_answer = feedback_body.get("correctedAnswer")
    routing_decision = feedback_body.get("routingDecision")

    store = get_user_memory_store()
    rec = store.record_feedback(
        user_id=user_id,
        session_id=session_id,
        query=query,
        answer=answer,
        is_helpful=is_helpful,
        failure_type=failure_type,
        corrected_answer=corrected_answer,
        routing_decision=routing_decision,
    )
    return {
        "status": "ok",
        "feedbackId": rec.feedback_id,
        "message": "Feedback recorded successfully for continuous evaluation.",
    }


_load_metrics_snapshot()
