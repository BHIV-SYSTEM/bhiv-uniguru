from __future__ import annotations

from typing import Dict, Any


CANONICAL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "धर्म": {
        "canonical_concept": "धर्म",
        "semantic_summary": "A canonical concept associated with order, duty, and civilizational coherence.",
        "epistemic_domain": "dharma",
        "governance_level": "governed",
    }
}


def get_concept_entry(concept: str) -> Dict[str, Any]:
    return CANONICAL_REGISTRY.get(concept, {
        "canonical_concept": concept,
        "semantic_summary": "A concept entered into the decoder without a curated registry entry.",
        "epistemic_domain": "unclassified",
        "governance_level": "governed",
    })
