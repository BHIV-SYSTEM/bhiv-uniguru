import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ontology.sanskrit_decoder import decode_sanskrit_concept, load_sanskar_registry
from service.ecosystem_runtime import execute_ecosystem_runtime, verify_ecosystem_replay

def main():
    print("Generating Phase 2 Sanskrit Decoder Proof Logs...")
    proof_dir = ROOT / "review_packets" / "proof_logs"
    integration_dir = ROOT / "review_packets" / "integration_proof"
    proof_dir.mkdir(parents=True, exist_ok=True)
    integration_dir.mkdir(parents=True, exist_ok=True)

    # 1. Concept Decodes
    concepts = [
        "dharma", "karma", "agni", "atman", "brahman", "prana", "rta", "shakti", "yajna", "om",
        "kala", "akasha", "guru", "vidya", "samskara", "maya", "prakrti", "purusha",
        "lokas", "koshas", "chakras", "moksha", "yoga"
    ]
    registry, metadata_by_id = load_sanskar_registry()
    print(f"Loaded {len(registry.list_concepts())} concepts from Sanskar registry.")

    results = {}
    for concept in concepts:
        res = decode_sanskrit_concept(concept)
        results[concept] = res
        proof_path = proof_dir / f"sanskrit_decoder_proof_{concept}_v2.json"
        proof_path.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Saved proof for {concept}: coverage={res['civilizational_knowledge']['coverage']['coverage_pct']}%, nodes={res['knowledge_graph']['metadata']['node_count']}")

    # 2. Graph Traversal Proof
    from ontology.sanskrit_decoder import traverse_concept_graph
    traverse_proof = traverse_concept_graph(
        start="prana",
        edge_types=["canonical_cross_reference", "related_kosha", "related_chakra"],
        max_depth=3,
        registry=registry,
        metadata_by_id=metadata_by_id,
    )
    traverse_path = proof_dir / "sanskrit_graph_traverse_proof_prana_v3.json"
    traverse_path.write_text(json.dumps(traverse_proof, indent=2, ensure_ascii=False), encoding="utf-8")

    # 3. Ecosystem Execution & Replay Proofs
    exec_proof = execute_ecosystem_runtime("dharma", trace_id="isha_phase2_dharma_execution", emit_proof=False)
    exec_path = integration_dir / "ecosystem_execution_isha_sanskrit_dharma_v2.json"
    exec_path.write_text(json.dumps(exec_proof, indent=2, ensure_ascii=False), encoding="utf-8")

    replay_proof = verify_ecosystem_replay("dharma", trace_id="isha_phase2_dharma_execution", emit_proof=False)
    replay_path = integration_dir / "replay_verification_isha_sanskrit_dharma_v2.json"
    replay_path.write_text(json.dumps(replay_proof, indent=2, ensure_ascii=False), encoding="utf-8")

    # Save latest integration proof
    latest_exec_path = integration_dir / "ecosystem_execution_latest.json"
    latest_exec_path.write_text(json.dumps(exec_proof, indent=2, ensure_ascii=False), encoding="utf-8")

    print("All Sanskrit Decoder Proof Logs Generated Successfully!")

if __name__ == "__main__":
    main()
