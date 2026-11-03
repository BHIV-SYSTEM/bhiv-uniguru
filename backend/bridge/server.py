import ipaddress
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlsplit

import jwt
import requests
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from contracts.schemas import AuditEventSchema, BridgeChatRequest, BridgeChatResponse
from core.engine import RuleEngine
from enforcement.enforcement import SovereignEnforcement
from integrations.gurukul.adapter import GurukulIntegrationAdapter, GurukulQueryRequest
from security.audit_emitter import AuditEmitter
from security.jwt_rs256 import RBACEnforcer, RS256Verifier
from security.replay_table import ReplayMitigationTable

app = FastAPI(title="UniGuru Sovereign Bridge")

PYTHON_ENGINE_URL = os.getenv("UNIGURU_ENGINE_URL", "http://127.0.0.1:8000/ask")
UNIGURU_API_TOKEN = os.getenv("UNIGURU_API_TOKEN", "").strip()
_BACKEND_ROOT = Path(__file__).resolve().parents[1]

engine = RuleEngine()
enforcer = SovereignEnforcement()
gurukul_adapter = GurukulIntegrationAdapter(engine=engine)
bearer_scheme = HTTPBearer(auto_error=False)
app.state.jwt_verifier = None
app.state.rbac_enforcer = RBACEnforcer(
    required_roles={"viewer", "user", "operator", "admin", "superadmin"}
)
app.state.replay_table = ReplayMitigationTable(
    persist_path=os.getenv(
        "UNIGURU_REPLAY_STORE_PATH",
        str(_BACKEND_ROOT / "logs" / "bridge_replay.json"),
    )
)
app.state.audit_emitter = AuditEmitter(
    os.getenv(
        "UNIGURU_BRIDGE_AUDIT_PATH",
        str(_BACKEND_ROOT / "logs" / "bridge_audit.jsonl"),
    )
)


def _validated_engine_url() -> str:
    engine_url = os.getenv("UNIGURU_ENGINE_URL", PYTHON_ENGINE_URL).strip()
    try:
        parsed = urlsplit(engine_url)
        parsed.port
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="Python engine URL configuration is invalid.") from exc
    if not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(status_code=503, detail="Python engine URL configuration is invalid.")

    if parsed.scheme == "https":
        return engine_url

    local_hosts = {"localhost"}
    try:
        if ipaddress.ip_address(parsed.hostname).is_loopback:
            local_hosts.add(parsed.hostname)
    except ValueError:
        pass

    local_development_http = (
        parsed.scheme == "http"
        and parsed.hostname.casefold() in {host.casefold() for host in local_hosts}
        and os.getenv("UNIGURU_ENV", "production").strip().casefold() == "development"
        and os.getenv("UNIGURU_ALLOW_LOCAL_HTTP", "").strip().casefold() == "true"
    )
    if local_development_http:
        return engine_url
    raise HTTPException(
        status_code=503,
        detail="Insecure Python engine transport is disabled; configure HTTPS.",
    )


def _configured_jwt_verifier(request: Request) -> RS256Verifier:
    verifier = request.app.state.jwt_verifier
    if verifier is None:
        try:
            verifier = RS256Verifier()
        except ValueError as exc:
            raise HTTPException(
                status_code=503,
                detail="Bridge JWT authentication is not configured.",
            ) from exc
        request.app.state.jwt_verifier = verifier
    return verifier


async def authenticate_chat_request(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Bearer authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = _configured_jwt_verifier(request).verify(credentials.credentials)
    except (PermissionError, ValueError, TypeError, OverflowError, jwt.PyJWTError) as exc:
        raise HTTPException(
            status_code=401,
            detail="Bearer token is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if not claims.sub.strip() or not claims.role.strip() or not claims.jti.strip():
        raise HTTPException(
            status_code=401,
            detail="Bearer token is missing required identity claims.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        request.app.state.rbac_enforcer.enforce(claims)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="Bearer token role is not authorized.") from exc

    try:
        request.app.state.replay_table.consume(claims.jti, exp=claims.exp)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="Bearer token replay detected.") from exc
    except OSError as exc:
        raise HTTPException(
            status_code=503,
            detail="Replay protection is unavailable.",
        ) from exc

    request.state.audit_actor = claims.sub
    request.state.audit_jti = claims.jti


@app.middleware("http")
async def audit_chat_requests(request: Request, call_next):
    if request.url.path != "/chat" or request.method != "POST":
        return await call_next(request)

    try:
        response = await call_next(request)
    except Exception:
        _emit_chat_audit(request, status_code=500)
        raise

    _emit_chat_audit(request, status_code=response.status_code)
    return response


def _emit_chat_audit(request: Request, status_code: int) -> None:
    event = AuditEventSchema(
        event="bridge_chat_request",
        actor=getattr(request.state, "audit_actor", "anonymous"),
        resource="/chat",
        outcome="ALLOW" if status_code < 400 else "DENY",
        metadata={
            "status_code": status_code,
            "jti": getattr(request.state, "audit_jti", None),
        },
    )
    request.app.state.audit_emitter.emit(
        event=event.event,
        actor=event.actor,
        resource=event.resource,
        outcome=event.outcome,
        metadata=event.metadata,
    )


def _extract_answer(payload: Dict[str, Any]) -> str:
    return str(
        payload.get("answer")
        or (payload.get("aiResponse") or {}).get("content")
        or (payload.get("data") or {}).get("response")
        or ""
    )


def _build_engine_headers(caller: str) -> Dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "X-Caller-Name": caller,
    }
    if UNIGURU_API_TOKEN:
        headers["Authorization"] = f"Bearer {UNIGURU_API_TOKEN}"
    return headers


@app.post("/chat", response_model=BridgeChatResponse)
async def chat_bridge(
    request: BridgeChatRequest,
    _: None = Depends(authenticate_chat_request),
):
    trace_id = str(uuid.uuid4())
    start_time = time.perf_counter()
    user_msg = request.message or request.question or request.query

    if not user_msg:
        raise HTTPException(status_code=400, detail="No valid query provided.")

    decision = engine.evaluate(
        user_msg,
        {
            "session_id": request.session_id,
            "trace_id": trace_id,
            "caller": request.caller,
        },
    )

    if decision.get("decision") == "forward":
        engine_url = _validated_engine_url()
        try:
            resp = requests.post(
                engine_url,
                json={
                    "query": user_msg,
                    "session_id": request.session_id,
                    "allow_web": bool(request.allow_web),
                    "context": {
                        **(request.context or {}),
                        "caller": request.caller,
                        "bridge_source": request.source,
                        "trace_id": trace_id,
                    },
                },
                headers=_build_engine_headers(request.caller),
                timeout=10,
            )
            resp.raise_for_status()
            engine_data = resp.json()

            answer = _extract_answer(engine_data)
            if not answer:
                decision = {
                    "decision": "block",
                    "verification_status": "UNVERIFIED",
                    "reason": "Python engine response not verifiable.",
                    "data": {"response_content": ""},
                }
            else:
                verification_status = str(engine_data.get("verification_status") or "UNVERIFIED").upper()
                truth_declaration = (
                    "VERIFIED"
                    if verification_status == "VERIFIED"
                    else "VERIFIED_PARTIAL"
                    if verification_status == "PARTIAL"
                    else "UNVERIFIED"
                )
                formatted_response = (
                    "Based on verified source: Python UniGuru engine"
                    if verification_status == "VERIFIED"
                    else "This information is partially verified from: Python UniGuru engine"
                    if verification_status == "PARTIAL"
                    else "Verification status: UNVERIFIED"
                )
                decision = {
                    "decision": engine_data.get("decision", "answer"),
                    "reason": engine_data.get("reason", "Response provided by Python UniGuru engine."),
                    "verification_status": verification_status,
                    "status_action": engine_data.get("status_action"),
                    "governance_flags": engine_data.get("governance_flags", {}),
                    "governance_output": engine_data.get("governance_output", {}),
                    "ontology_reference": engine_data.get("ontology_reference"),
                    "reasoning_trace": engine_data.get("reasoning_trace"),
                    "data": {
                        "response_content": answer,
                        "verification": {
                            "source_name": "Python UniGuru engine",
                            "truth_declaration": truth_declaration,
                            "formatted_response": formatted_response,
                        },
                        "engine_response": engine_data,
                    },
                    "forwarded_to": engine_url,
                }

        except Exception as exc:
            decision = {
                "decision": "block",
                "verification_status": "UNVERIFIED",
                "reason": f"Python engine unavailable: {str(exc)}",
                "data": {"response_content": ""},
            }

    sealed_response = enforcer.process_and_seal(decision, trace_id)

    if not enforcer.verify_bridge_seal(sealed_response):
        raise HTTPException(status_code=500, detail="Enforcement Seal Violation: Tampering Detected.")

    latency = (time.perf_counter() - start_time) * 1000
    sealed_response["latency_ms"] = round(latency, 2)
    sealed_response["trace_id"] = trace_id

    return sealed_response


@app.post("/integrations/gurukul/chat")
async def gurukul_chat(request: GurukulQueryRequest):
    if not request.student_query.strip():
        raise HTTPException(status_code=400, detail="student_query is required.")
    return gurukul_adapter.process_student_query(request)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "bridge_version": "3.0.0",
        "python_engine_target": os.getenv("UNIGURU_ENGINE_URL", PYTHON_ENGINE_URL),
        "external_llm_calls": bool(os.getenv("UNIGURU_LLM_URL")),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
