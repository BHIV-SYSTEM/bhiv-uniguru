from ontology.sanskrit.registry import SanskritRegistry
from ontology.sanskrit.schema import (
    sanskrit_concept_from_dict,
    sanskrit_concept_to_dict,
)


def _concept_payload():
    return {
        "concept_id": "test:sanskrit:karma",
        "canonical_name": "karma",
        "sanskrit": "कर्म",
        "transliteration": "karma",
        "shabda": "action",
        "dhatu": "kṛ",
        "vyakarana": "test grammar",
        "nirukta": "test derivation",
        "beeja": None,
        "tattva": None,
        "shakti": None,
        "functional_meaning": "action and its consequences",
        "related_concepts": ["dharma"],
        "ontology_version": "test-v1",
        "semantic_version": "test-v1",
    }


def test_sanskrit_registry_relations_are_immutable_and_detached_from_input():
    payload = _concept_payload()
    concept = sanskrit_concept_from_dict(payload)
    registry = SanskritRegistry()
    registry.register(concept)

    payload["related_concepts"].append("unverified")

    assert registry.get(concept.concept_id).related_concepts == ("dharma",)
    assert sanskrit_concept_to_dict(registry.get(concept.concept_id))["related_concepts"] == ["dharma"]
