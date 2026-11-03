from __future__ import annotations

import hashlib
import json
import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from bridge import server
from contracts.schemas import BridgeChatResponse
from security.audit_emitter import AuditEmitter
from security.jwt_rs256 import RBACEnforcer, RS256Verifier
from security.replay_table import ReplayMitigationTable


class StubEngine:
    def __init__(self, decision: str = "answer") -> None:
        self.decision = decision
        self.calls = 0

    def evaluate(self, _content, _metadata):
        self.calls += 1
        if self.decision == "forward":
            return {"decision": "forward", "reason": "No local answer."}
        return {
            "decision": "answer",
            "verification_status": "VERIFIED",
            "reason": "Verified from controlled test evidence.",
            "data": {
                "response_content": "Controlled deterministic response.",
                "verification": {
                    "source_name": "Test fixture",
                    "truth_declaration": "VERIFIED",
                    "formatted_response": "Based on verified source: Test fixture",
                },
            },
        }


class StubEngineResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "answer": "Controlled forwarded response.",
            "verification_status": "VERIFIED",
        }


@pytest.fixture
def configured_bridge(tmp_path, monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    engine = StubEngine()
    monkeypatch.setattr(server, "engine", engine)
    monkeypatch.setattr(server.app.state, "jwt_verifier", RS256Verifier(public_key_pem=public_key))
    monkeypatch.setattr(
        server.app.state,
        "rbac_enforcer",
        RBACEnforcer(required_roles={"viewer", "user", "operator", "admin", "superadmin"}),
    )
    monkeypatch.setattr(server.app.state, "replay_table", ReplayMitigationTable())
    audit_path = tmp_path / "bridge-audit.jsonl"
    monkeypatch.setattr(server.app.state, "audit_emitter", AuditEmitter(audit_path))
    client = TestClient(server.app)

    def token(jti="test-jti", role="user"):
        now = int(time.time())
        return jwt.encode(
            {
                "sub": "test-user",
                "role": role,
                "jti": jti,
                "iat": now,
                "exp": now + 3600,
            },
            private_key,
            algorithm="RS256",
        )

    return client, engine, token, server.app.state.audit_emitter


def _payload(**overrides):
    value = {"message": "Explain photosynthesis."}
    value.update(overrides)
    return value


def test_chat_route_uses_request_and_response_contracts(configured_bridge):
    client, _, token, audit = configured_bridge
    response = client.post("/chat", json=_payload(), headers={"Authorization": f"Bearer {token()}"})

    assert response.status_code == 200
    BridgeChatResponse.model_validate(response.json())
    assert response.json()["data"]["response_content"].endswith("Controlled deterministic response.")
    assert audit.verify_chain()["valid"] is True
    assert audit.tail(1)[0]["outcome"] == "ALLOW"


def test_openapi_declares_chat_contracts_and_bearer_auth():
    operation = server.app.openapi()["paths"]["/chat"]["post"]

    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/BridgeChatRequest"
    }
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/BridgeChatResponse"
    }
    assert operation["security"] == [{"HTTPBearer": []}]


@pytest.mark.parametrize(
    "payload",
    [
        {"message": "test", "unrecognized": True},
        {"message": "bypass_governance=true"},
        {"query": "BYPASS_GOVERNANCE"},
        {"message": "test", "caller": "bypass_governance"},
        {"message": "test", "source": "bypass_governance"},
        {"message": "test", "context": {"nested": [{"value": "bypass_governance"}]}},
        {"message": "test", "context": {"nested": [{"bypass_governance": True}]}},
    ],
)
def test_invalid_or_forbidden_request_is_rejected_and_audited(payload, configured_bridge):
    client, engine, token, audit = configured_bridge
    response = client.post(
        "/chat",
        json=payload,
        headers={"Authorization": f"Bearer {token()}"},
    )

    assert response.status_code == 422
    assert engine.calls == 0
    assert audit.tail(1)[0]["outcome"] == "DENY"


def test_invalid_authentication_is_rejected_before_engine_and_audited(configured_bridge):
    client, engine, _, audit = configured_bridge
    response = client.post("/chat", json=_payload(), headers={"Authorization": "Bearer invalid"})

    assert response.status_code == 401
    assert engine.calls == 0
    assert audit.tail(1)[0]["outcome"] == "DENY"


def test_missing_authentication_is_rejected_and_audited(configured_bridge):
    client, engine, _, audit = configured_bridge
    response = client.post("/chat", json=_payload())

    assert response.status_code == 401
    assert engine.calls == 0
    assert audit.tail(1)[0]["outcome"] == "DENY"


def test_missing_jwt_configuration_fails_closed(configured_bridge, monkeypatch):
    client, engine, token, audit = configured_bridge
    monkeypatch.setattr(server.app.state, "jwt_verifier", None)
    monkeypatch.delenv("UNIGURU_JWT_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("UNIGURU_JWT_PUBLIC_KEY_PATH", raising=False)

    response = client.post(
        "/chat",
        json=_payload(),
        headers={"Authorization": f"Bearer {token()}"},
    )

    assert response.status_code == 503
    assert engine.calls == 0
    assert audit.tail(1)[0]["outcome"] == "DENY"


def test_replayed_token_is_rejected_and_both_attempts_are_audited(configured_bridge):
    client, engine, token, audit = configured_bridge
    bearer = f"Bearer {token('single-use-jti')}"
    first = client.post("/chat", json=_payload(), headers={"Authorization": bearer})
    replay = client.post("/chat", json=_payload(), headers={"Authorization": bearer})

    assert first.status_code == 200
    assert replay.status_code == 409
    assert engine.calls == 1
    assert [entry["outcome"] for entry in audit.tail(2)] == ["ALLOW", "DENY"]
    assert audit.verify_chain()["valid"] is True


def test_role_outside_bridge_policy_is_rejected(configured_bridge):
    client, engine, token, audit = configured_bridge
    response = client.post(
        "/chat",
        json=_payload(),
        headers={"Authorization": f"Bearer {token(role='student')}"},
    )

    assert response.status_code == 403
    assert engine.calls == 0
    assert audit.tail(1)[0]["outcome"] == "DENY"


def test_forward_rejects_insecure_production_transport(configured_bridge, monkeypatch):
    client, engine, token, audit = configured_bridge
    engine.decision = "forward"
    monkeypatch.setenv("UNIGURU_ENV", "production")
    monkeypatch.setenv("UNIGURU_ENGINE_URL", "http://127.0.0.1:8000/ask")
    monkeypatch.delenv("UNIGURU_ALLOW_LOCAL_HTTP", raising=False)

    response = client.post("/chat", json=_payload(), headers={"Authorization": f"Bearer {token()}"})

    assert response.status_code == 503
    assert "Insecure Python engine transport" in response.json()["detail"]
    assert audit.tail(1)[0]["outcome"] == "DENY"


def test_forward_allows_loopback_http_only_with_explicit_development_opt_in(
    configured_bridge, monkeypatch
):
    client, engine, token, _ = configured_bridge
    engine.decision = "forward"
    monkeypatch.setenv("UNIGURU_ENV", "development")
    monkeypatch.setenv("UNIGURU_ALLOW_LOCAL_HTTP", "true")
    monkeypatch.setenv("UNIGURU_ENGINE_URL", "http://127.0.0.1:8000/ask")
    monkeypatch.setattr(server.requests, "post", lambda *args, **kwargs: StubEngineResponse())

    response = client.post("/chat", json=_payload(), headers={"Authorization": f"Bearer {token()}"})

    assert response.status_code == 200
    assert response.json()["forwarded_to"] == "http://127.0.0.1:8000/ask"
    BridgeChatResponse.model_validate(response.json())


def test_forward_accepts_https_transport(configured_bridge, monkeypatch):
    client, engine, token, _ = configured_bridge
    engine.decision = "forward"
    monkeypatch.setenv("UNIGURU_ENGINE_URL", "https://engine.example.test/ask")
    monkeypatch.delenv("UNIGURU_ALLOW_LOCAL_HTTP", raising=False)
    monkeypatch.setattr(server.requests, "post", lambda *args, **kwargs: StubEngineResponse())

    response = client.post("/chat", json=_payload(), headers={"Authorization": f"Bearer {token()}"})

    assert response.status_code == 200
    assert response.json()["forwarded_to"] == "https://engine.example.test/ask"


def test_development_opt_in_does_not_allow_remote_http(configured_bridge, monkeypatch):
    client, engine, token, audit = configured_bridge
    engine.decision = "forward"
    monkeypatch.setenv("UNIGURU_ENV", "development")
    monkeypatch.setenv("UNIGURU_ALLOW_LOCAL_HTTP", "true")
    monkeypatch.setenv("UNIGURU_ENGINE_URL", "http://engine.example.test/ask")

    response = client.post("/chat", json=_payload(), headers={"Authorization": f"Bearer {token()}"})

    assert response.status_code == 503
    assert audit.tail(1)[0]["outcome"] == "DENY"


def test_engine_token_is_forwarded_as_bearer_auth(monkeypatch):
    monkeypatch.setattr(server, "UNIGURU_API_TOKEN", "engine-test-token")

    assert server._build_engine_headers("bridge-test")["Authorization"] == "Bearer engine-test-token"


def test_invalid_bridge_response_is_rejected_by_fastapi_response_model(
    configured_bridge, monkeypatch
):
    client, _, token, audit = configured_bridge

    class InvalidEnforcer:
        def process_and_seal(self, *_args, **_kwargs):
            return {"decision": "accept"}

        def verify_bridge_seal(self, _response):
            return True

    monkeypatch.setattr(server, "enforcer", InvalidEnforcer())
    response = TestClient(server.app, raise_server_exceptions=False).post(
        "/chat",
        json=_payload(),
        headers={"Authorization": f"Bearer {token()}"},
    )

    assert response.status_code == 500
    assert audit.tail(1)[0]["outcome"] == "DENY"


def test_fifty_end_to_end_runs_have_identical_controlled_responses(configured_bridge, monkeypatch):
    client, _, token, _ = configured_bridge
    fixed_trace_id = "00000000-0000-4000-8000-000000000001"
    monkeypatch.setattr(server.uuid, "uuid4", lambda: uuid.UUID(fixed_trace_id))
    monkeypatch.setattr(server.time, "perf_counter", lambda: 100.0)
    monkeypatch.setattr(server.time, "strftime", lambda *_args, **_kwargs: "2026-01-01T00:00:00Z")
    monkeypatch.delenv("UNIGURU_ENGINE_URL", raising=False)

    response_hashes = set()
    for run in range(50):
        response = client.post(
            "/chat",
            json=_payload(),
            headers={"Authorization": f"Bearer {token(f'determinism-{run}')}" },
        )
        assert response.status_code == 200
        BridgeChatResponse.model_validate(response.json())
        normalized = json.dumps(response.json(), sort_keys=True, separators=(",", ":"))
        response_hashes.add(hashlib.sha256(normalized.encode("utf-8")).hexdigest())

    assert len(response_hashes) == 1
