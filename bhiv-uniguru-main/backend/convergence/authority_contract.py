"""
Authority Contract Module
Defines explicit authority classifications for all UniGuru knowledge sources.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


class AuthorityTier(str, Enum):
    CANONICAL = "CANONICAL"
    DERIVED = "DERIVED"
    FALLBACK = "FALLBACK"
    TEST_FIXTURE = "TEST_FIXTURE"
    LEGACY = "LEGACY"


@dataclass
class KnowledgeSourceDefinition:
    source_key: str
    name: str
    authority_tier: AuthorityTier
    is_queried: bool
    influences_answers: bool
    has_provenance: bool
    rebuildable: bool
    rebuild_path: str
    governance_owner: str
    description: str


class KnowledgeAuthorityMap:
    """Registry maintaining explicit authority classifications for all knowledge sources."""

    def __init__(self) -> None:
        self._sources: Dict[str, KnowledgeSourceDefinition] = {}
        self._bootstrap_map()

    def _bootstrap_map(self) -> None:
        sources = [
            KnowledgeSourceDefinition(
                source_key="MASTERDB",
                name="Balbharti MasterDB Curriculum Dataset",
                authority_tier=AuthorityTier.CANONICAL,
                is_queried=True,
                influences_answers=True,
                has_provenance=True,
                rebuildable=True,
                rebuild_path="masterdb/coverage_validator.py",
                governance_owner="MDU / Isha",
                description="Canonical curriculum ground truth for school education.",
            ),
            KnowledgeSourceDefinition(
                source_key="AKASHIC",
                name="Akashic Kosha Knowledge Core",
                authority_tier=AuthorityTier.CANONICAL,
                is_queried=True,
                influences_answers=True,
                has_provenance=True,
                rebuildable=True,
                rebuild_path="backend/kosha/kosha_loader.py",
                governance_owner="MDU / Isha",
                description="Canonical primary Kosha knowledge objects.",
            ),
            KnowledgeSourceDefinition(
                source_key="KNOWLEDGE_GRAPH",
                name="Civilizational Knowledge Graph",
                authority_tier=AuthorityTier.CANONICAL,
                is_queried=True,
                influences_answers=True,
                has_provenance=True,
                rebuildable=True,
                rebuild_path="backend/ontology/graph.py",
                governance_owner="Isha / Sanskar",
                description="Structured entity relations, Darśana matrix, Pāṇini sūtras.",
            ),
            KnowledgeSourceDefinition(
                source_key="KOSHA_JSON",
                name="Local Kosha Entries Store",
                authority_tier=AuthorityTier.CANONICAL,
                is_queried=True,
                influences_answers=True,
                has_provenance=True,
                rebuildable=True,
                rebuild_path="backend/kosha/kosha_enforcer.py",
                governance_owner="Isha",
                description="Validated Kosha JSON records.",
            ),
            KnowledgeSourceDefinition(
                source_key="MARKDOWN_CORPUS",
                name="Domain Markdown Records",
                authority_tier=AuthorityTier.CANONICAL,
                is_queried=True,
                influences_answers=True,
                has_provenance=True,
                rebuildable=True,
                rebuild_path="backend/loaders/file_parser.py",
                governance_owner="Isha",
                description="Domain markdown knowledge files (Sanskrit, Quantum, Jain, etc.).",
            ),
            KnowledgeSourceDefinition(
                source_key="FAISS_VECTOR_INDEX",
                name="FAISS Vector Candidate Index",
                authority_tier=AuthorityTier.DERIVED,
                is_queried=True,
                influences_answers=True,
                has_provenance=True,
                rebuildable=True,
                rebuild_path="scripts/rebuild_faiss_index.py",
                governance_owner="Vijay (Search Engine)",
                description="Derived vector index for candidate retrieval acceleration.",
            ),
            KnowledgeSourceDefinition(
                source_key="LLM_FALLBACK",
                name="Unverified LLM Fallback Engine",
                authority_tier=AuthorityTier.FALLBACK,
                is_queried=False,
                influences_answers=True,
                has_provenance=False,
                rebuildable=False,
                rebuild_path="N/A",
                governance_owner="Vijay / Isha",
                description="Generative completion fallback when no canonical evidence passes.",
            ),
            KnowledgeSourceDefinition(
                source_key="TEST_FIXTURE",
                name="Local Unit Test Fixtures",
                authority_tier=AuthorityTier.TEST_FIXTURE,
                is_queried=False,
                influences_answers=False,
                has_provenance=True,
                rebuildable=True,
                rebuild_path="backend/tests/fixtures/",
                governance_owner="Isha",
                description="Test mocks forbidden from production query runs.",
            ),
        ]
        for src in sources:
            self._sources[src.source_key] = src

    def get_source(self, key: str) -> Optional[KnowledgeSourceDefinition]:
        return self._sources.get(key.upper())

    def get_tier(self, key: str) -> AuthorityTier:
        src = self.get_source(key)
        return src.authority_tier if src else AuthorityTier.FALLBACK

    def to_dict(self) -> Dict[str, Any]:
        return {
            key: {
                "source_key": s.source_key,
                "name": s.name,
                "authority_tier": s.authority_tier.value,
                "is_queried": s.is_queried,
                "influences_answers": s.influences_answers,
                "has_provenance": s.has_provenance,
                "rebuildable": s.rebuildable,
                "rebuild_path": s.rebuild_path,
                "governance_owner": s.governance_owner,
                "description": s.description,
            }
            for key, s in self._sources.items()
        }


_GLOBAL_AUTHORITY_MAP: Optional[KnowledgeAuthorityMap] = None


def get_authority_map() -> KnowledgeAuthorityMap:
    global _GLOBAL_AUTHORITY_MAP
    if _GLOBAL_AUTHORITY_MAP is None:
        _GLOBAL_AUTHORITY_MAP = KnowledgeAuthorityMap()
    return _GLOBAL_AUTHORITY_MAP
