"""
TANTRA Gated Bridge — Pydantic v1.0 Interface Schemas
T-GOV-F01 / UG-HO-02

All inbound and outbound payloads for the Sovereign Bridge must validate
against these models.  Zero-trust hard-fail: any field violation raises a
422 before the request reaches business logic.

Forbidden patterns enforced at schema level:
  - bypass_governance  (field must never be present)
  - insecure_transport (scheme must be https in any URL field)
"""
from __future__ import annotations

import re
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------

_SAFE_STRING_RE = re.compile(r"^[^\x00-\x1f]{1,4096}$")


def _require_safe(value: str, field_name: str) -> str:
    if not _SAFE_STRING_RE.match(value):
        raise ValueError(f"{field_name} contains control characters or exceeds 4096 chars")
    return value


def _reject_forbidden_governance(value: Any, location: str) -> None:
    pending = [value]
    while pending:
        current = pending.pop()
        if isinstance(current, str):
            if "bypass_governance" in current.casefold():
                raise ValueError(f"bypass_governance is forbidden in {location}")
        elif isinstance(current, dict):
            pending.extend(current.keys())
            pending.extend(current.values())
        elif isinstance(current, (list, tuple)):
            pending.extend(current)


# ---------------------------------------------------------------------------
# Inbound: BridgeChatRequest  (POST /chat)
# ---------------------------------------------------------------------------

class BridgeChatRequest(BaseModel):
    """Inbound payload for the Sovereign Bridge /chat endpoint."""

    message: Optional[str] = Field(None, max_length=4096)
    question: Optional[str] = Field(None, max_length=4096)
    query: Optional[str] = Field(None, max_length=4096)
    session_id: Optional[str] = Field(None, max_length=128)
    caller: str = Field("uniguru-frontend", max_length=128)
    allow_web: bool = False
    context: Optional[Dict[str, Any]] = None
    source: str = Field("bridge_v3", max_length=64)

    @model_validator(mode="after")
    def _require_at_least_one_query_field(self) -> "BridgeChatRequest":
        if not (self.message or self.question or self.query):
            raise ValueError("At least one of message, question, or query must be provided")
        return self

    @field_validator("caller", "source", mode="before")
    @classmethod
    def _no_bypass_governance(cls, v: str) -> str:
        _reject_forbidden_governance(v, "caller/source")
        return v

    @field_validator("message", "question", "query", mode="before")
    @classmethod
    def _no_bypass_governance_in_query(cls, v: Optional[str]) -> Optional[str]:
        _reject_forbidden_governance(v, "query text")
        return v

    @field_validator("context", mode="before")
    @classmethod
    def _context_no_forbidden_keys(cls, v: Any) -> Any:
        _reject_forbidden_governance(v, "context")
        return v

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Outbound: VerificationBlock
# ---------------------------------------------------------------------------

class VerificationBlock(BaseModel):
    source_name: str = Field(..., max_length=256)
    truth_declaration: Literal["VERIFIED", "VERIFIED_PARTIAL", "UNVERIFIED"]
    formatted_response: str = Field(..., max_length=4096)


# ---------------------------------------------------------------------------
# Outbound: BridgeResponseData
# ---------------------------------------------------------------------------

class BridgeResponseData(BaseModel):
    response_content: str = Field(..., max_length=65536)
    verification: Optional[VerificationBlock] = None
    engine_response: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Outbound: BridgeChatResponse  (returned by POST /chat)
# ---------------------------------------------------------------------------

class BridgeChatResponse(BaseModel):
    """Outbound payload from the Sovereign Bridge /chat endpoint."""

    decision: Literal["answer", "block", "forward"]
    verification_status: Literal["VERIFIED", "PARTIAL", "UNVERIFIED"]
    status_action: Literal["ALLOW", "ALLOW_WITH_DISCLAIMER", "REFUSE"]
    reason: str = Field(..., max_length=1024)
    data: BridgeResponseData
    enforcement_signature: str = Field(..., min_length=64, max_length=64)
    enforced: bool
    request_id: str = Field(..., max_length=128)
    sealed_at: str = Field(..., max_length=32)
    trace_id: str = Field(..., max_length=128)
    latency_ms: float = Field(..., ge=0.0)
    verification_prefix: Optional[str] = Field(None, max_length=512)
    disclaimer: Optional[str] = Field(None, max_length=512)
    forwarded_to: Optional[str] = Field(None, max_length=512)
    governance_flags: Optional[Dict[str, Any]] = None
    governance_output: Optional[Dict[str, Any]] = None
    ontology_reference: Optional[str] = Field(None, max_length=512)
    reasoning_trace: Optional[Any] = None

    @field_validator("enforcement_signature", mode="before")
    @classmethod
    def _signature_is_hex(cls, v: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", str(v)):
            raise ValueError("enforcement_signature must be a 64-character lowercase hex SHA-256")
        return v

    model_config = {"extra": "ignore"}


# ---------------------------------------------------------------------------
# Outbound: HealthResponse  (GET /health)
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "error"]
    bridge_version: str = Field(..., max_length=32)
    python_engine_target: str = Field(..., max_length=512)
    external_llm_calls: bool

    model_config = {"extra": "ignore"}


# ---------------------------------------------------------------------------
# Governance audit event schema (used by AuditEmitter callers)
# ---------------------------------------------------------------------------

class AuditEventSchema(BaseModel):
    event: str = Field(..., max_length=128)
    actor: str = Field(..., max_length=256)
    resource: str = Field(..., max_length=512)
    outcome: Literal["ALLOW", "DENY"]
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("event", "actor", "resource", mode="before")
    @classmethod
    def _no_control_chars(cls, v: str) -> str:
        return _require_safe(str(v), "field")

    model_config = {"extra": "forbid"}
