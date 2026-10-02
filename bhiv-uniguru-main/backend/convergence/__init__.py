"""
UniGuru Knowledge Convergence & Trust Validation Layer
Owner: Isha Singh

Exports authority contracts, canonical knowledge objects, retrieval evidence contracts,
claim-to-evidence bindings, and the convergence runtime engine.
"""

from .authority_contract import AuthorityTier, KnowledgeAuthorityMap, get_authority_map
from .canonical_object import CanonicalKnowledgeObject, create_canonical_object
from .retrieval_evidence_contract import (
    RetrievedEvidenceItem,
    RetrievalRunRecord,
    ClaimEvidenceBinding,
    ClaimVerificationStatus,
)
from .convergence_runtime import KnowledgeConvergenceRuntime, run_convergence_pipeline

__all__ = [
    "AuthorityTier",
    "KnowledgeAuthorityMap",
    "get_authority_map",
    "CanonicalKnowledgeObject",
    "create_canonical_object",
    "RetrievedEvidenceItem",
    "RetrievalRunRecord",
    "ClaimEvidenceBinding",
    "ClaimVerificationStatus",
    "KnowledgeConvergenceRuntime",
    "run_convergence_pipeline",
]
