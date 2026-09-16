"""
Canonical Knowledge Object Module
MDU-compliant schema for retrievable evidence objects in UniGuru.
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from memory.constitutional_semantic_memory import stable_hash
from convergence.authority_contract import AuthorityTier


SCHEMA_VERSION = "UNIGURU_CANONICAL_OBJECT_V1"


@dataclass(frozen=True)
class CanonicalKnowledgeObject:
    """Canonical retrievable knowledge object."""

    canonical_object_id: str
    concept_id: str
    ksml_id: str
    source_id: str
    authority_tier: AuthorityTier
    tradition_context: str
    text_span: str
    provenance_hash: str
    schema_version: str = SCHEMA_VERSION
    knowledge_version: str = "1.0.0"
    parent_derived_relations: List[str] = field(default_factory=list)
    graph_relations: List[str] = field(default_factory=list)
    domain: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["authority_tier"] = self.authority_tier.value
        return data


def create_canonical_object(
    concept_id: str,
    source_id: str,
    text_span: str,
    authority_tier: AuthorityTier = AuthorityTier.CANONICAL,
    ksml_id: Optional[str] = None,
    tradition_context: str = "general",
    domain: Optional[str] = None,
    tags: Optional[List[str]] = None,
    parent_derived_relations: Optional[List[str]] = None,
    graph_relations: Optional[List[str]] = None,
    knowledge_version: str = "1.0.0",
) -> CanonicalKnowledgeObject:
    clean_concept = (concept_id or "unclassified_concept").strip().lower()
    clean_ksml = (ksml_id or f"ksml:{clean_concept}").strip().lower()
    clean_source = (source_id or "unknown_source").strip()
    clean_span = (text_span or "").strip()

    hash_payload = {
        "concept_id": clean_concept,
        "ksml_id": clean_ksml,
        "source_id": clean_source,
        "text_span": clean_span,
        "authority_tier": authority_tier.value,
        "tradition": tradition_context,
        "version": knowledge_version,
    }
    prov_hash = stable_hash(hash_payload)
    obj_id = f"uko:{clean_concept}:{prov_hash[:12]}"

    return CanonicalKnowledgeObject(
        canonical_object_id=obj_id,
        concept_id=clean_concept,
        ksml_id=clean_ksml,
        source_id=clean_source,
        authority_tier=authority_tier,
        tradition_context=tradition_context,
        text_span=clean_span,
        provenance_hash=prov_hash,
        schema_version=SCHEMA_VERSION,
        knowledge_version=knowledge_version,
        parent_derived_relations=parent_derived_relations or [],
        graph_relations=graph_relations or [],
        domain=domain,
        tags=tags or [],
    )
