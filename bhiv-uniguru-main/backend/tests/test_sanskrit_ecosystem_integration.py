from __future__ import annotations

from service.ecosystem_runtime import execute_ecosystem_runtime, verify_ecosystem_replay


def test_sanskrit_decoder_uses_existing_ecosystem_bucket_insightflow_and_replay():
    execution = execute_ecosystem_runtime("धर्म", trace_id="test_sanskrit_dharma", emit_proof=False)
    replay = verify_ecosystem_replay("धर्म", trace_id="test_sanskrit_dharma", emit_proof=False)

    decoder = execution["pipeline_summary"]["sanskrit_decoder"]
    assert decoder["canonical_concept"]["concept_id"] == "sanskar:sanskrit:dharma"
    assert execution["bucket_telemetry"]["emitted"] is True
    assert execution["insightflow_observability"]["trace_complete"] is True
    assert replay["replay_verified"] is True
    assert replay["checks"]["sanskrit_decoder_result_stable"] is True
