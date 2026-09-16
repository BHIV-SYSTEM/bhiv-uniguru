from uniguru_sanskrit_decoder.decoder import decode_sanskrit_concept
from uniguru_sanskrit_decoder.runtime import DecoderRuntime


def test_decode_sanskrit_concept_returns_traceable_pipeline():
    result = decode_sanskrit_concept("धर्म")

    assert result["canonical_concept"] == "धर्म"
    assert result["pipeline"][0]["stage"] == "Śabda"
    assert result["pipeline"][-1]["stage"] == "Governed UniGuru Response"
    assert result["provenance"]["source"] == "canonical-registry"
    assert result["evidence_classification"] == "governed"
    assert all(step["provenance"]["trace_id"] for step in result["pipeline"])


def test_runtime_exposes_replay_safe_execution():
    runtime = DecoderRuntime()
    result = runtime.execute("धर्म")

    assert result["replay_safe"] is True
    assert result["execution_metadata"]["replay_id"].startswith("replay-")
    assert result["knowledge_graph"]["nodes"]
