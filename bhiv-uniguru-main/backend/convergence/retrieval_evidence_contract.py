"""
Retrieval Evidence Contract & Claim Binding Module
Defines explicit contracts between retrieval, reranking, and answer synthesis.
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from memory.constitutional_semantic_memory import stable_hash
from convergence.authority_contract import AuthorityTier
from convergence.canonical_object import CanonicalKnowledgeObject


class ClaimVerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    DERIVED = "DERIVED"
    UNVERIFIED_FALLBACK = "UNVERIFIED_FALLBACK"
    CONTRADICTED = "CONTRADICTED"


@dataclass
class RetrievedEvidenceItem:
    canonical_object_id: str
    source_id: str
    authority_tier: AuthorityTier
    provenance_hash: str
    ranking_score: float
    dedup_status: str  # "unique", "deduplicated_alias", "deduplicated_chunk"
    text_span: str
    domain: Optional[str] = None
    tradition_context: str = "general"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["authority_tier"] = self.authority_tier.value
        return data


@dataclass
class ClaimEvidenceBinding:
    claim_id: str
    claim_text: str
    canonical_object_id: str
    source_id: str
    text_span: str
    verification_status: ClaimVerificationStatus
    confidence: float
    provenance_hash: str

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["verification_status"] = self.verification_status.value
        return data


@dataclass
class RetrievalRunRecord:
    query_id: str
    trace_id: str
    canonical_concept_id: str
    semantic_scope: str
    retrieval_run_id: str
    index_version: str
    candidate_count: int
    deduplicated_candidate_count: int
    selected_evidence: List[RetrievedEvidenceItem]
    claim_bindings: List[ClaimEvidenceBinding]
    verification_status: str
    replay_id: str
    replay_safe: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "trace_id": self.trace_id,
            "canonical_concept_id": self.canonical_concept_id,
            "semantic_scope": self.semantic_scope,
            "retrieval_run_id": self.retrieval_run_id,
            "index_version": self.index_version,
            "candidate_count": self.candidate_count,
            "deduplicated_candidate_count": self.deduplicated_candidate_count,
            "selected_evidence": [e.to_dict() for e in self.selected_evidence],
            "claim_bindings": [cb.to_dict() for cb in self.claim_bindings],
            "verification_status": self.verification_status,
            "replay_id": self.replay_id,
            "replay_safe": self.replay_safe,
        }
