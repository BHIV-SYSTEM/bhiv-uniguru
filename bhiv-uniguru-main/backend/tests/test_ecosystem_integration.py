from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from service.ecosystem_runtime import execute_ecosystem_runtime
from service.uniguru_runtime_api import app


def test_execute_ecosystem_runtime_emits_evidence():
    temp_dir = tempfile.mkdtemp(prefix="ecosystem_test_")
    proof_dir = Path(temp_dir) / "proofs"
    try:
        result = execute_ecosystem_runtime(
            query="What is the Bhagavad Gita?",
            proof_dir=proof_dir,
            emit_proof=True,
        )

        assert result["trace_id"].startswith("ecosystem_")
        assert result["vijay_validation"]["replay_safe"] is True
        assert result["tantra_contract"]["verification_status"] in {"VERIFIED", "NO_VERIFIED_KNOWLEDGE", "PARTIAL"}
        assert result["bucket_telemetry"]["emitted"] is True
        assert result["insightflow_observability"]["trace_complete"] is True
        assert result["gc_validation"]["authority_enforced"] is True
        assert result["mdu_validation"]["schema_compatible"] is True
        assert (proof_dir / "ecosystem_execution_latest.json").exists()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_ecosystem_replay_endpoint_verifies_stable_cross_service_fields():
    client = TestClient(app)
    response = client.post(
        "/runtime/ecosystem/replay",
        json={
            "query": "What is the Bhagavad Gita?",
            "trace_id": "ecosystem_replay_test",
            "emit_proof": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["replay_verified"] is True
    assert all(payload["checks"].values())


def test_mitra_endpoint_redacts_internal_governance_details():
    client = TestClient(app)
    response = client.post(
        "/mitra/ecosystem/ask",
        json={
            "query": "What is the Bhagavad Gita?",
            "trace_id": "ecosystem_mitra_test",
            "emit_proof": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trace_id"] == "ecosystem_mitra_test"
    assert payload["replay_safe"] is True
    assert "vijay_validation" not in payload
    assert "gc_validation" not in payload
    assert "mdu_validation" not in payload
