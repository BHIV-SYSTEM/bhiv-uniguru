from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ontology.sanskrit_decoder import (
    decode_sanskrit_concept,
    load_sanskar_registry,
    traverse_concept_graph,
)
from service.uniguru_runtime_api import app


def test_sanskar_source_retrieval_supports_all_supplied_concepts():
    registry, _ = load_sanskar_registry()
    assert len(registry.list_concepts()) >= 21
    result = decode_sanskrit_concept("धर्म")
    replay = decode_sanskrit_concept("dharma")
    assert result["canonical_concept"]["concept_id"] == "sanskar:sanskrit:dharma"
    assert result["result_hash"] == replay["result_hash"]
    assert [layer["stage"] for layer in result["pipeline"]] == ["śabda", "dhātu", "vyākaraṇa", "nirukta", "bīja", "tattva", "śakti", "functional_meaning"]
    assert result["provenance"]["source_documents"]
    assert result["knowledge_graph"]["metadata"]["consistency_valid"] is True
    assert result["civilizational_knowledge"]["coverage"]["coverage_pct"] >= 85.0


def test_registry_builds_without_markdown_corpus(monkeypatch):
    monkeypatch.setattr("ontology.sanskrit_decoder.SOURCE_DIR", Path("c:/does/not/exist"))
    registry, metadata = load_sanskar_registry()
    assert len(registry.list_concepts()) >= 10
    assert metadata["sanskar:sanskrit:dharma"]["retrieval_system"] == "uniguru_ecosystem_adapter"


def test_sanskar_decoder_supports_lokas_koshas_chakras():
    for query in ["lokas", "koshas", "chakras"]:
        res = decode_sanskrit_concept(query)
        assert res["canonical_concept"] is not None
        assert res["civilizational_knowledge"]["layers"]["cosmology"]["status"] == "EVIDENCE_BACKED"
        assert res["knowledge_graph"]["metadata"]["consistency_valid"] is True


def test_unknown_concept_is_explicitly_unverified_without_inference():
    result = decode_sanskrit_concept("अनिर्धारित")
    assert result["pipeline"] == []
    assert result["governed_response"]["evidence_classification"]["classification"] == "UNVERIFIED"
    assert result["governed_response"]["governance_state"] == "no_inference"


def test_sanskrit_runtime_endpoint_validates_and_returns_source_scoped_payload():
    client = TestClient(app)
    response = client.post("/runtime/sanskrit/decode", json={"query": "धर्म", "emit_proof": False})
    assert response.status_code == 200
    payload = response.json()
    assert payload["decoder_result"]["pipeline"][0]["stage"] == "śabda"
    assert len(payload["governed_response"]["evidence_classification"]["evidence_types"]) > 0
    assert client.post("/runtime/sanskrit/decode", json={"query": "   ", "emit_proof": False}).status_code == 422

    # Test v2 endpoint alias
    v2_response = client.post("/v2/runtime/sanskrit/decode", json={"query": "lokas", "emit_proof": False})
    assert v2_response.status_code == 200
    v2_payload = v2_response.json()
    assert v2_payload["decoder_result"]["canonical_concept"]["canonical_name"] == "lokas"


# ── Phase 3 Tests ─────────────────────────────────────────────────────────────

def test_panini_sutra_layer_is_structured_and_source_backed():
    """Phase 3: vyākaraṇa layer must expose structured Pāṇini sūtra records."""
    result = decode_sanskrit_concept("dharma")
    ck = result["civilizational_knowledge"]
    vyakarana_layer = ck["layers"]["vyakarana"]
    assert vyakarana_layer["status"] == "EVIDENCE_BACKED"
    # Phase 3 enrichment: panini_grammar sub-key must exist
    assert "panini_grammar" in vyakarana_layer
    pg = vyakarana_layer["panini_grammar"]
    assert pg["status"] == "EVIDENCE_BACKED"
    assert len(pg["panini_sutras"]) > 0
    sutra = pg["panini_sutras"][0]
    assert "sutra_number" in sutra
    assert "sutra_text" in sutra
    assert "rule_class" in sutra
    assert sutra["provenance"]["evidence_type"] == "PANINI"


def test_acoustic_phonetic_layer_is_evidence_backed():
    """Phase 3: bīja layer must expose Śikṣā-sourced acoustic metadata."""
    result = decode_sanskrit_concept("dharma")
    ck = result["civilizational_knowledge"]
    beeja_layer = ck["layers"]["beeja"]
    assert beeja_layer["status"] == "EVIDENCE_BACKED"
    assert "acoustic_phonetics" in beeja_layer
    ap = beeja_layer["acoustic_phonetics"]
    assert ap["status"] == "EVIDENCE_BACKED"
    assert len(ap["claims"]) > 0
    acoustic_val = ap["claims"][0]["value"]
    assert "ipa" in acoustic_val
    assert "varna_class" in acoustic_val
    assert "sthana" in acoustic_val
    assert "siksha_source" in acoustic_val
    # Provenance must be sourced to Śikṣā (VEDA evidence_type)
    assert ap["claims"][0]["provenance"][0]["evidence_type"] == "VEDA"


def test_comparative_hermeneutics_matrix_is_populated():
    """Phase 3: comparative_hermeneutics layer must expose a structured Darśana matrix."""
    result = decode_sanskrit_concept("dharma")
    ck = result["civilizational_knowledge"]
    assert "comparative_hermeneutics" in ck["layers"]
    herm = ck["layers"]["comparative_hermeneutics"]
    assert herm["status"] == "EVIDENCE_BACKED"
    matrix = herm["darshana_matrix"]
    # Dharma has at least advaita, vishishtadvaita, dvaita, mimamsa, buddhist, jain
    assert "advaita" in matrix
    assert "dvaita" in matrix
    assert "mimamsa" in matrix
    assert "buddhist" in matrix
    # Each entry must have position and source_text
    for key, entry in matrix.items():
        assert "position" in entry, f"{key} missing 'position'"
        assert "source_text" in entry, f"{key} missing 'source_text'"
        assert "evidence_type" in entry, f"{key} missing 'evidence_type'"


def test_graph_traversal_multi_hop_returns_provenance_chain():
    """Phase 3: traverse_concept_graph must return multi-hop path with provenance."""
    registry, metadata_by_id = load_sanskar_registry()
    result = traverse_concept_graph(
        start="prana",
        edge_types=["canonical_cross_reference"],
        max_depth=2,
        registry=registry,
        metadata_by_id=metadata_by_id,
    )
    assert "error" not in result
    assert len(result["path"]) >= 1
    assert result["path"][0]["node_label"] == "prana"
    assert result["path"][0]["hop"] == 0
    assert result["traversal_metadata"]["replay_safe"] is True
    assert result["sub_graph"]["node_count"] > 0
    assert result["sub_graph"]["edge_count"] >= 0
    # All path frames must have provenance
    for frame in result["path"]:
        assert "node_id" in frame
        assert "hop" in frame


def test_graph_traverse_endpoint_validates_depth_and_returns_path():
    """Phase 3: /v2/runtime/sanskrit/graph/traverse must accept query and return traversal."""
    client = TestClient(app)
    # Valid traversal
    resp = client.post(
        "/v2/runtime/sanskrit/graph/traverse",
        json={"start": "dharma", "edge_types": ["canonical_cross_reference"], "max_depth": 2, "emit_proof": False},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "traversal_result" in payload
    tr = payload["traversal_result"]
    assert tr["start"] == "dharma"
    assert len(tr["path"]) >= 1
    assert tr["path"][0]["node_label"] == "dharma"
    assert "sub_graph" in tr
    assert payload["replay_safe"] is True
    # Depth exceeding max (7 > 6) must be clamped by the endpoint validator
    bad_resp = client.post(
        "/v2/runtime/sanskrit/graph/traverse",
        json={"start": "karma", "max_depth": 7, "emit_proof": False},
    )
    assert bad_resp.status_code == 422  # Pydantic validates max_depth <= 6


def test_recursive_typed_node_traversal_prana_kosha_chakra_bija():
    """Phase 4: Verify recursive traversal across typed nodes: Prāṇa -> Kosha -> Chakra -> Bīja."""
    registry, metadata_by_id = load_sanskar_registry()
    result = traverse_concept_graph(
        start="prana",
        edge_types=None,
        max_depth=3,
        registry=registry,
        metadata_by_id=metadata_by_id,
    )
    assert "error" not in result
    path_nodes = {frame["node_id"]: frame for frame in result["path"]}
    path_types = {frame["node_type"] for frame in result["path"]}

    # Must contain sanskrit_concept, kosha, chakra, and bija node types
    assert "sanskrit_concept" in path_types
    assert "kosha" in path_types
    assert "chakra" in path_types
    assert "bija" in path_types

    # Verify key typed nodes are present in traversal path
    assert "sanskar:sanskrit:prana" in path_nodes
    assert "kosha_ref:pranamaya_kosha" in path_nodes
    assert "chakra_ref:anahata" in path_nodes
    assert "bija_ref:yam" in path_nodes

    # Verify provenance exists on every path frame
    for frame in result["path"]:
        assert frame["provenance"] is not None
        assert frame["node_type"] is not None

    # Verify provenance exists on every sub-graph edge
    for edge in result["sub_graph"]["edges"]:
        assert "provenance" in edge
        assert "from_type" in edge
        assert "to_type" in edge

