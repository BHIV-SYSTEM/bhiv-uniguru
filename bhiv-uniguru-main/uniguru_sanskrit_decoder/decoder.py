from __future__ import annotations

from typing import Any, Dict, List

from .governance import build_provenance
from .graph import build_knowledge_graph
from .registry import get_concept_entry
from .schemas import PIPELINE_STAGES, build_schema_payload


def _build_step(stage: str, concept: str, detail: str, provenance: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "stage": stage,
        "concept": concept,
        "detail": detail,
        "provenance": provenance,
    }


def decode_sanskrit_concept(concept: str) -> Dict[str, Any]:
    provenance = build_provenance()
    entry = get_concept_entry(concept)
    pipeline: List[Dict[str, Any]] = []
    for stage in PIPELINE_STAGES:
        if stage == "Śabda":
            detail = f"Phonetic and linguistic framing of {concept}."
        elif stage == "Dhātu":
            detail = f"Root semantics associated with {concept}."
        elif stage == "Vyākaraṇa":
            detail = f"Grammatical and syntactic structure of {concept}."
        elif stage == "Nirukta":
            detail = f"Etymological and interpretive derivation of {concept}."
        elif stage == "Bīja":
            detail = f"Seed conceptual force behind {concept}."
        elif stage == "Tattva":
            detail = f"Ontological principle embodied by {concept}."
        elif stage == "Śakti":
            detail = f"Operational power and dynamic force of {concept}."
        elif stage == "Functional Meaning":
            detail = f"Practical, contextual meaning of {concept}."
        elif stage == "Cross References":
            detail = f"Related concepts linked to {concept}."
        elif stage == "Civilizational Knowledge Graph":
            detail = f"Civilizational relations for {concept}."
        elif stage == "Research Classification":
            detail = f"Research classification for {concept}."
        else:
            detail = f"Governed response for {concept}."
        pipeline.append(_build_step(stage, concept, detail, provenance))

    result = build_schema_payload(concept, pipeline, provenance)
    result.update(
        {
            "canonical_concept": concept,
            "semantic_summary": entry["semantic_summary"],
            "epistemic_domain": entry["epistemic_domain"],
            "governance_level": entry["governance_level"],
            "functional_meaning": f"The civilizational meaning of {concept} is preserved through a governed pipeline.",
            "cross_references": [f"{concept}-related"],
            "knowledge_graph": build_knowledge_graph(pipeline),
        }
    )
    return result
