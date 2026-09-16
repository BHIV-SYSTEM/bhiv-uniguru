from __future__ import annotations

from integrations.tantra_sdk_adapter import TantraSdkAdapter
from service.ecosystem_runtime import execute_ecosystem_runtime


def test_tantra_sdk_execution_event_is_emitted_and_schema_compatible():
    adapter = TantraSdkAdapter()
    event = adapter.build_execution_event(
        trace_id="tantra_sdk_test_trace",
        query="What is the Bhagavad Gita?",
        verification_status="VERIFIED",
        answer="The Bhagavad Gita is a scripture of dialogue and ethics.",
        domain="spirituality",
        duration_ms=12,
    )

    assert event["schema_version"] == "execution_event.v1.0.0"
    assert event["trace_id"] == "tantra_sdk_test_trace"
    assert event["validation_status"] == "valid"
    assert event["status"] == "completed"
    assert event["command"] == "What is the Bhagavad Gita?"
    assert event["subject_id"] == "uniguru_runtime"
    assert event["outcome"]["verification_status"] == "VERIFIED"

    runtime_result = execute_ecosystem_runtime(
        query="What is the Bhagavad Gita?",
        emit_proof=False,
        trace_id="tantra_sdk_runtime_test",
    )
    tantra_contracts = runtime_result.get("tantra_sdk_contracts", {})
    assert "execution_event" in tantra_contracts
    assert tantra_contracts["execution_event"]["trace_id"] == "tantra_sdk_runtime_test"
