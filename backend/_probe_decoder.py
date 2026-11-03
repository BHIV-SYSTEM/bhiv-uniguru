"""Corrected live probe — UG-HO-02 component audit."""
import json, sys, traceback, time
from pathlib import Path

# Ensure retrieval/ (repo root) is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

results = {}

# ── 1. Sanskrit registry ──────────────────────────────────────────────────────
try:
    from ontology.sanskrit_decoder import load_sanskar_registry
    reg, meta = load_sanskar_registry()
    concepts = reg.list_concepts()
    results["registry_concept_count"] = len(concepts)
    results["registry_concept_ids"] = [str(c).split("concept_id='")[1].split("'")[0] for c in concepts]
    results["registry_meta_type"] = str(type(meta))
    results["registry_meta_key_count"] = len(meta) if isinstance(meta, dict) else "n/a"
except Exception:
    results["registry_error"] = traceback.format_exc()

# ── 2. Decode supported concept: dharma ──────────────────────────────────────
try:
    from ontology.sanskrit_decoder import decode_sanskrit_concept
    r_dharma = decode_sanskrit_concept("dharma")
    results["dharma_decode_keys"] = list(r_dharma.keys()) if isinstance(r_dharma, dict) else str(type(r_dharma))
    results["dharma_source_paths"] = r_dharma.get("source_paths", [])
    results["dharma_result_hash"] = str(r_dharma.get("result_hash", ""))[:32]
    results["dharma_graph_node_count"] = r_dharma.get("graph_node_count")
    results["dharma_evidence_count"] = len(r_dharma.get("evidence", []))
    results["dharma_status"] = r_dharma.get("status")
    results["dharma_found"] = r_dharma.get("found")
except Exception:
    results["dharma_error"] = traceback.format_exc()

# ── 3. Decode unsupported concept ────────────────────────────────────────────
try:
    r_bad = decode_sanskrit_concept("nonexistent_xyz_concept_12345")
    results["unsupported_keys"] = list(r_bad.keys()) if isinstance(r_bad, dict) else str(type(r_bad))
    results["unsupported_found"] = r_bad.get("found")
    results["unsupported_status"] = r_bad.get("status")
    results["unsupported_evidence_count"] = len(r_bad.get("evidence", []))
except Exception:
    results["unsupported_error"] = traceback.format_exc()

# ── 4. Determinism: decode dharma twice, compare hashes ──────────────────────
try:
    r_a = decode_sanskrit_concept("dharma")
    r_b = decode_sanskrit_concept("dharma")
    h_a = r_a.get("result_hash") if isinstance(r_a, dict) else None
    h_b = r_b.get("result_hash") if isinstance(r_b, dict) else None
    results["dharma_deterministic"] = (h_a == h_b) if (h_a and h_b) else "no_hash_field"
    results["dharma_hash_sample"] = str(h_a)[:32] if h_a else None
except Exception:
    results["determinism_error"] = traceback.format_exc()

# ── 5. Graph traversal ────────────────────────────────────────────────────────
try:
    from ontology.sanskrit_decoder import traverse_concept_graph, load_sanskar_registry
    reg2, meta2 = load_sanskar_registry()
    g = traverse_concept_graph("dharma", edge_types=None, max_depth=2, registry=reg2, metadata_by_id=meta2)
    results["graph_traversal_type"] = str(type(g))
    results["graph_traversal_keys"] = list(g.keys()) if isinstance(g, dict) else str(g)[:200]
    results["graph_node_count"] = g.get("node_count") or len(g.get("nodes", {}))
    results["graph_edge_count"] = g.get("edge_count") or len(g.get("edges", []))
except Exception:
    results["graph_traversal_error"] = traceback.format_exc()

# ── 6. Kosha loader (correct signature) ──────────────────────────────────────
try:
    from kosha.kosha_loader import KoshaLoader
    from pathlib import Path as P
    kosha_dir = str(P(__file__).parent / "data" / "kosha")
    loader = KoshaLoader(data_sources=[kosha_dir])
    entries = loader.load_all()
    results["kosha_entry_count"] = len(entries)
    if entries:
        s = entries[0]
        results["kosha_sample_keys"] = list(s.keys()) if isinstance(s, dict) else str(type(s))
        results["kosha_sample_domain"] = s.get("domain") if isinstance(s, dict) else None
        results["kosha_sample_id"] = s.get("knowledge_id") if isinstance(s, dict) else None
        results["kosha_sample_tags"] = s.get("tags", [])[:5] if isinstance(s, dict) else None
except Exception:
    results["kosha_loader_error"] = traceback.format_exc()

# ── 7. Kosha retriever ────────────────────────────────────────────────────────
try:
    from kosha.kosha_retriever import KoshaRetriever
    retriever = KoshaRetriever(entries)
    import inspect
    sig = str(inspect.signature(retriever.retrieve))
    results["kosha_retriever_retrieve_sig"] = sig
    hits = retriever.retrieve("drip irrigation water conservation")
    results["kosha_retriever_hits"] = len(hits) if isinstance(hits, list) else str(type(hits))
    if isinstance(hits, list) and hits:
        h = hits[0]
        results["kosha_retriever_sample"] = {
            "knowledge_id": h.get("knowledge_id") if isinstance(h, dict) else str(h)[:80],
            "confidence": h.get("confidence") if isinstance(h, dict) else None,
            "domain": h.get("domain") if isinstance(h, dict) else None,
        }
except Exception:
    results["kosha_retriever_error"] = traceback.format_exc()

# ── 8. MasterDB retrieval (correct signature) ────────────────────────────────
try:
    from retrieval.retrieval_engine import find_top_matches, load_masterdb_records
    records = load_masterdb_records()
    results["masterdb_record_count"] = len(records)
    m_result = find_top_matches("addition of numbers", grade=1, subject="Mathematics")
    results["masterdb_matches_type"] = str(type(m_result))
    results["masterdb_matches_keys"] = list(m_result.keys()) if isinstance(m_result, dict) else str(m_result)[:200]
except Exception:
    results["masterdb_error"] = traceback.format_exc()

# ── 9. MasterDB filter guard (grade mismatch → no results) ───────────────────
try:
    bad = find_top_matches("addition", grade=99)
    if isinstance(bad, dict):
        candidates = bad.get("candidates") or bad.get("results") or bad.get("matches") or []
        results["masterdb_filter_guard"] = len(candidates) == 0
        results["masterdb_filter_guard_raw"] = str(bad)[:200]
    else:
        results["masterdb_filter_guard"] = len(bad) == 0 if isinstance(bad, list) else "unknown"
except Exception:
    results["masterdb_filter_error"] = traceback.format_exc()

# ── 10. Convergence runtime ───────────────────────────────────────────────────
try:
    from convergence.convergence_runtime import run_convergence_pipeline, get_authority_map
    auth_map = get_authority_map()
    results["authority_map_sources"] = list(auth_map.keys()) if isinstance(auth_map, dict) else str(type(auth_map))
    results["convergence_pipeline_importable"] = True
except Exception:
    results["convergence_runtime_error"] = traceback.format_exc()

# ── 11. Ontology graph (correct constructor) ──────────────────────────────────
try:
    from ontology.graph import OntologyGraph
    from ontology.snapshots.snapshot_v1 import load_snapshot
    snap = load_snapshot()
    results["ontology_snapshot_type"] = str(type(snap))
except Exception:
    try:
        from ontology.snapshot_manager import SnapshotManager
        sm = SnapshotManager()
        results["snapshot_manager_loaded"] = True
        results["snapshot_manager_methods"] = [m for m in dir(sm) if not m.startswith("_")]
    except Exception:
        results["ontology_graph_error"] = traceback.format_exc()

# ── 12. Sanskrit schema immutability (correct constructor) ────────────────────
try:
    from ontology.sanskrit.schema import SanskritConcept
    c = SanskritConcept(
        concept_id="test:test",
        canonical_name="test",
        sanskrit="परीक्षा",
        transliteration="Parīkṣā",
        shabda="परीक्षा",
        dhatu="परि + ईक्ष् — to examine",
        vyakarana="test grammar",
        nirukta="test nirukta",
        beeja=None,
        tattva=None,
        shakti=None,
        functional_meaning="test meaning",
        related_concepts=["karma", "dharma"],
        ontology_version="test_v1",
        semantic_version="test_v1",
    )
    results["sanskrit_schema_related_type"] = type(c.related_concepts).__name__
    results["sanskrit_schema_immutable"] = isinstance(c.related_concepts, tuple)
    # Mutation attempt
    try:
        c.related_concepts.append("yoga")
        results["sanskrit_schema_mutation_blocked"] = False
    except AttributeError:
        results["sanskrit_schema_mutation_blocked"] = True
except Exception:
    results["sanskrit_schema_error"] = traceback.format_exc()

# ── 13. Security + contracts import ──────────────────────────────────────────
try:
    from contracts.schemas import BridgeChatRequest, BridgeChatResponse, AuditEventSchema
    from security.jwt_rs256 import RS256Verifier, RBACEnforcer
    from security.replay_table import ReplayMitigationTable
    from security.audit_emitter import AuditEmitter
    results["security_contracts_import"] = "OK"
except Exception:
    results["security_contracts_error"] = traceback.format_exc()

# ── 14. Provenance: check source_reference in MasterDB records ───────────────
try:
    import json as _json
    from pathlib import Path as _P
    ds = _json.loads((_P(__file__).parent.parent / "masterdb" / "balbharti" / "canonical_dataset.json").read_text(encoding="utf-8"))
    missing_ref = sum(1 for r in ds if not (r.get("source_lineage") or {}).get("source_reference"))
    results["masterdb_provenance_total"] = len(ds)
    results["masterdb_provenance_missing_source_reference"] = missing_ref
    results["masterdb_provenance_gate_passes"] = len(ds) - missing_ref
    results["masterdb_isbns"] = list({(r.get("source_lineage") or {}).get("isbn","") for r in ds})
    results["masterdb_grades"] = sorted({(r.get("source_lineage") or {}).get("grade","") for r in ds})
    results["masterdb_subjects"] = sorted({(r.get("source_lineage") or {}).get("subject","") for r in ds})
    results["masterdb_mediums"] = sorted({(r.get("source_lineage") or {}).get("medium","") for r in ds})
except Exception:
    results["masterdb_provenance_error"] = traceback.format_exc()

print(json.dumps(results, indent=2, default=str))
