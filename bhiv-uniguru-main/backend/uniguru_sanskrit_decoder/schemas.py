from __future__ import annotations

from typing import Any, Dict, List


PIPELINE_STAGES: List[str] = [
    "Śabda",
    "Dhātu",
    "Vyākaraṇa",
    "Nirukta",
    "Bīja",
    "Tattva",
    "Śakti",
    "Functional Meaning",
    "Cross References",
    "Civilizational Knowledge Graph",
    "Research Classification",
    "Governed UniGuru Response",
]


def build_schema_payload(concept: str, pipeline: List[Dict[str, Any]], provenance: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "canonical_concept": concept,
        "pipeline": pipeline,
        "provenance": provenance,
        "evidence_classification": "governed",
        "semantic_stability": "deterministic",
        "knowledge_graph_contract": "native-uniguru",
    }
