"""
Unit + Negative tests — TANTRA Gated Bridge Schema Contracts
T-GOV-F01

Covers:
  - BridgeChatRequest: valid payloads, missing query, forbidden patterns,
    extra fields, oversized fields
  - BridgeChatResponse: valid construction, bad signature format
  - AuditEventSchema: valid, forbidden pattern, control characters
  - HealthResponse: valid, bad status literal
  - EnforcementSealer: determinism, signature verification, tamper detection
  - SovereignEnforcement: VERIFIED / PARTIAL / UNVERIFIED paths, seal integrity
"""
from __future__ import annotations

import hashlib
import uuid

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_chat_request(**overrides):
    base = {"message": "What is photosynthesis?", "caller": "test-caller"}
    base.update(overrides)
    return base


def _valid_chat_response(**overrides):
    sig = hashlib.sha256(b"content" + b"req-id").hexdigest()
    base = {
        "decision": "answer",
        "verification_status": "VERIFIED",
        "status_action": "ALLOW",
        "reason": "Verified from KB",
        "data": {
            "response_content": "Photosynthesis is the process...",
            "verification": {
                "source_name": "UniGuru KB",
                "truth_declaration": "VERIFIED",
                "formatted_response": "Based on verified source: UniGuru KB",
            },
        },
        "enforcement_signature": sig,
        "enforced": True,
        "request_id": "req-id",
        "sealed_at": "2026-01-01T00:00:00Z",
        "trace_id": str(uuid.uuid4()),
        "latency_ms": 42.5,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# BridgeChatRequest — valid
# ---------------------------------------------------------------------------

def test_chat_request_valid_message():
    from contracts.schemas import BridgeChatRequest
    req = BridgeChatRequest(**_valid_chat_request())
    assert req.message == "What is photosynthesis?"


def test_chat_request_valid_question_field():
    from contracts.schemas import BridgeChatRequest
    req = BridgeChatRequest(question="What is gravity?", caller="test")
    assert req.question == "What is gravity?"


def test_chat_request_valid_query_field():
    from contracts.schemas import BridgeChatRequest
    req = BridgeChatRequest(query="Explain osmosis", caller="test")
    assert req.query == "Explain osmosis"


def test_chat_request_defaults():
    from contracts.schemas import BridgeChatRequest
    req = BridgeChatRequest(message="hello")
    assert req.caller == "uniguru-frontend"
    assert req.allow_web is False
    assert req.source == "bridge_v3"


# ---------------------------------------------------------------------------
# BridgeChatRequest — missing query (negative)
# ---------------------------------------------------------------------------

def test_chat_request_no_query_field_raises():
    from contracts.schemas import BridgeChatRequest
    with pytest.raises(ValidationError, match="At least one of"):
        BridgeChatRequest(caller="test")


def test_chat_request_all_query_fields_none_raises():
    from contracts.schemas import BridgeChatRequest
    with pytest.raises(ValidationError):
        BridgeChatRequest(message=None, question=None, query=None, caller="test")


# ---------------------------------------------------------------------------
# BridgeChatRequest — forbidden pattern (negative)
# ---------------------------------------------------------------------------

def test_chat_request_bypass_governance_in_caller_raises():
    from contracts.schemas import BridgeChatRequest
    with pytest.raises(ValidationError, match="bypass_governance"):
        BridgeChatRequest(message="hello", caller="bypass_governance_caller")


def test_chat_request_bypass_governance_in_source_raises():
    from contracts.schemas import BridgeChatRequest
    with pytest.raises(ValidationError, match="bypass_governance"):
        BridgeChatRequest(message="hello", source="bypass_governance_hook")


def test_chat_request_bypass_governance_in_context_key_raises():
    from contracts.schemas import BridgeChatRequest
    with pytest.raises(ValidationError, match="bypass_governance"):
        BridgeChatRequest(message="hello", context={"bypass_governance": True})


def test_chat_request_bypass_governance_case_insensitive_raises():
    from contracts.schemas import BridgeChatRequest
    with pytest.raises(ValidationError, match="bypass_governance"):
        BridgeChatRequest(message="hello", caller="BYPASS_GOVERNANCE")


# ---------------------------------------------------------------------------
# BridgeChatRequest — extra fields forbidden (negative)
# ---------------------------------------------------------------------------

def test_chat_request_extra_field_raises():
    from contracts.schemas import BridgeChatRequest
    with pytest.raises(ValidationError):
        BridgeChatRequest(message="hello", unknown_field="bad")


# ---------------------------------------------------------------------------
# BridgeChatRequest — oversized field (negative)
# ---------------------------------------------------------------------------

def test_chat_request_message_too_long_raises():
    from contracts.schemas import BridgeChatRequest
    with pytest.raises(ValidationError):
        BridgeChatRequest(message="x" * 4097)


def test_chat_request_caller_too_long_raises():
    from contracts.schemas import BridgeChatRequest
    with pytest.raises(ValidationError):
        BridgeChatRequest(message="hello", caller="c" * 129)


# ---------------------------------------------------------------------------
# BridgeChatResponse — valid
# ---------------------------------------------------------------------------

def test_chat_response_valid():
    from contracts.schemas import BridgeChatResponse
    resp = BridgeChatResponse(**_valid_chat_response())
    assert resp.decision == "answer"
    assert resp.status_action == "ALLOW"
    assert len(resp.enforcement_signature) == 64


# ---------------------------------------------------------------------------
# BridgeChatResponse — bad signature (negative)
# ---------------------------------------------------------------------------

def test_chat_response_short_signature_raises():
    from contracts.schemas import BridgeChatResponse
    data = _valid_chat_response(enforcement_signature="abc123")
    with pytest.raises(ValidationError, match="64-character"):
        BridgeChatResponse(**data)


def test_chat_response_non_hex_signature_raises():
    from contracts.schemas import BridgeChatResponse
    data = _valid_chat_response(enforcement_signature="Z" * 64)
    with pytest.raises(ValidationError, match="64-character"):
        BridgeChatResponse(**data)


def test_chat_response_uppercase_hex_signature_raises():
    from contracts.schemas import BridgeChatResponse
    sig = hashlib.sha256(b"x").hexdigest().upper()
    data = _valid_chat_response(enforcement_signature=sig)
    with pytest.raises(ValidationError, match="64-character"):
        BridgeChatResponse(**data)


# ---------------------------------------------------------------------------
# BridgeChatResponse — bad literal values (negative)
# ---------------------------------------------------------------------------

def test_chat_response_bad_decision_raises():
    from contracts.schemas import BridgeChatResponse
    data = _valid_chat_response(decision="approve")
    with pytest.raises(ValidationError):
        BridgeChatResponse(**data)


def test_chat_response_bad_status_action_raises():
    from contracts.schemas import BridgeChatResponse
    data = _valid_chat_response(status_action="PASS")
    with pytest.raises(ValidationError):
        BridgeChatResponse(**data)


def test_chat_response_bad_verification_status_raises():
    from contracts.schemas import BridgeChatResponse
    data = _valid_chat_response(verification_status="UNKNOWN")
    with pytest.raises(ValidationError):
        BridgeChatResponse(**data)


# ---------------------------------------------------------------------------
# AuditEventSchema
# ---------------------------------------------------------------------------

def test_audit_event_valid():
    from contracts.schemas import AuditEventSchema
    ev = AuditEventSchema(event="jwt_verified", actor="user-1",
                          resource="/chat", outcome="ALLOW")
    assert ev.outcome == "ALLOW"


def test_audit_event_bad_outcome_raises():
    from contracts.schemas import AuditEventSchema
    with pytest.raises(ValidationError):
        AuditEventSchema(event="e", actor="a", resource="r", outcome="PERMIT")


def test_audit_event_extra_field_raises():
    from contracts.schemas import AuditEventSchema
    with pytest.raises(ValidationError):
        AuditEventSchema(event="e", actor="a", resource="r",
                         outcome="ALLOW", unknown="x")


def test_audit_event_control_char_in_event_raises():
    from contracts.schemas import AuditEventSchema
    with pytest.raises(ValidationError):
        AuditEventSchema(event="bad\x00event", actor="a",
                         resource="r", outcome="ALLOW")


# ---------------------------------------------------------------------------
# HealthResponse
# ---------------------------------------------------------------------------

def test_health_response_valid():
    from contracts.schemas import HealthResponse
    h = HealthResponse(status="ok", bridge_version="3.0.0",
                       python_engine_target="http://localhost:8000/ask",
                       external_llm_calls=False)
    assert h.status == "ok"


def test_health_response_bad_status_raises():
    from contracts.schemas import HealthResponse
    with pytest.raises(ValidationError):
        HealthResponse(status="running", bridge_version="3.0.0",
                       python_engine_target="http://localhost:8000/ask",
                       external_llm_calls=False)


# ---------------------------------------------------------------------------
# EnforcementSealer — determinism and tamper detection
# ---------------------------------------------------------------------------

def test_sealer_same_inputs_produce_same_signature():
    from enforcement.seal import EnforcementSealer
    s1 = EnforcementSealer.create_signature("hello world", "req-001")
    s2 = EnforcementSealer.create_signature("hello world", "req-001")
    assert s1 == s2


def test_sealer_different_content_produces_different_signature():
    from enforcement.seal import EnforcementSealer
    s1 = EnforcementSealer.create_signature("content A", "req-001")
    s2 = EnforcementSealer.create_signature("content B", "req-001")
    assert s1 != s2


def test_sealer_verify_valid_signature():
    from enforcement.seal import EnforcementSealer
    sig = EnforcementSealer.create_signature("payload", "req-xyz")
    assert EnforcementSealer.verify_signature("payload", "req-xyz", sig) is True


def test_sealer_verify_tampered_content_fails():
    from enforcement.seal import EnforcementSealer
    sig = EnforcementSealer.create_signature("original", "req-xyz")
    assert EnforcementSealer.verify_signature("tampered", "req-xyz", sig) is False


def test_sealer_verify_tampered_request_id_fails():
    from enforcement.seal import EnforcementSealer
    sig = EnforcementSealer.create_signature("content", "req-001")
    assert EnforcementSealer.verify_signature("content", "req-002", sig) is False


def test_sealer_fifty_runs_deterministic():
    from enforcement.seal import EnforcementSealer
    hashes = {EnforcementSealer.create_signature("fixed-content", "fixed-id")
              for _ in range(50)}
    assert len(hashes) == 1, "Non-deterministic signature across 50 runs"


# ---------------------------------------------------------------------------
# SovereignEnforcement — VERIFIED path
# ---------------------------------------------------------------------------

def test_enforcement_verified_path_allows():
    from enforcement.enforcement import SovereignEnforcement
    enforcer = SovereignEnforcement()
    decision = {
        "decision": "answer",
        "verification_status": "VERIFIED",
        "data": {
            "response_content": "Photosynthesis converts light to energy.",
            "verification": {
                "source_name": "UniGuru KB",
                "truth_declaration": "VERIFIED",
                "formatted_response": "Based on verified source: UniGuru KB",
            },
        },
    }
    result = enforcer.process_and_seal(decision, "req-001")
    assert result["status_action"] == "ALLOW"
    assert result["enforced"] is True
    assert len(result["enforcement_signature"]) == 64


def test_enforcement_verified_seal_verifies():
    from enforcement.enforcement import SovereignEnforcement
    enforcer = SovereignEnforcement()
    decision = {
        "verification_status": "VERIFIED",
        "data": {"response_content": "Answer text."},
    }
    result = enforcer.process_and_seal(decision, "req-002")
    assert enforcer.verify_bridge_seal(result) is True


# ---------------------------------------------------------------------------
# SovereignEnforcement — PARTIAL path
# ---------------------------------------------------------------------------

def test_enforcement_partial_path_allows_with_disclaimer():
    from enforcement.enforcement import SovereignEnforcement
    enforcer = SovereignEnforcement()
    decision = {
        "verification_status": "PARTIAL",
        "data": {"response_content": "Partial answer."},
    }
    result = enforcer.process_and_seal(decision, "req-003")
    assert result["status_action"] == "ALLOW_WITH_DISCLAIMER"
    assert "disclaimer" in result


# ---------------------------------------------------------------------------
# SovereignEnforcement — UNVERIFIED path (negative)
# ---------------------------------------------------------------------------

def test_enforcement_unverified_path_refuses():
    from enforcement.enforcement import SovereignEnforcement
    enforcer = SovereignEnforcement()
    decision = {
        "verification_status": "UNVERIFIED",
        "data": {"response_content": "Some unverified content."},
    }
    result = enforcer.process_and_seal(decision, "req-004")
    assert result["status_action"] == "REFUSE"
    assert result["decision"] == "block"


def test_enforcement_unverified_content_is_replaced():
    from enforcement.enforcement import SovereignEnforcement
    enforcer = SovereignEnforcement()
    decision = {
        "verification_status": "UNVERIFIED",
        "data": {"response_content": "Secret unverified data."},
    }
    result = enforcer.process_and_seal(decision, "req-005")
    assert "Secret unverified data" not in result["data"]["response_content"]


# ---------------------------------------------------------------------------
# SovereignEnforcement — tampered seal detection (negative)
# ---------------------------------------------------------------------------

def test_enforcement_tampered_content_fails_seal_check():
    from enforcement.enforcement import SovereignEnforcement
    enforcer = SovereignEnforcement()
    decision = {
        "verification_status": "VERIFIED",
        "data": {"response_content": "Original answer."},
    }
    result = enforcer.process_and_seal(decision, "req-006")
    # Tamper the content after sealing
    result["data"]["response_content"] = "Tampered answer."
    assert enforcer.verify_bridge_seal(result) is False


def test_enforcement_missing_signature_fails_seal_check():
    from enforcement.enforcement import SovereignEnforcement
    enforcer = SovereignEnforcement()
    result = {"data": {"response_content": "x"}, "request_id": "r"}
    assert enforcer.verify_bridge_seal(result) is False
