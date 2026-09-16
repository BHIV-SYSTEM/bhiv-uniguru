"""
Knowledge Convergence Runtime Module
Orchestrates canonical evidence validation, claim-to-evidence binding,
and deterministic replay record emission.
"""

import re
import uuid
from typing import Dict, Any, List, Optional, Tuple
from memory.constitutional_semantic_memory import stable_hash
from convergence.authority_contract import AuthorityTier, get_authority_map
from convergence.canonical_object import CanonicalKnowledgeObject, create_canonical_object
from convergence.retrieval_evidence_contract import (
    RetrievedEvidenceItem,
    ClaimEvidenceBinding,
    ClaimVerificationStatus,
    RetrievalRunRecord,
)

INDEX_VERSION = "UNIGURU_CONVERGENCE_INDEX_V1"


def _clean_tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[\w'-]+", (text or "").lower()) if len(t) > 1}


class KnowledgeConvergenceRuntime:
    """Orchestrates candidate deduplication, authority validation, and claim binding."""

    def __init__(self) -> None:
        self.authority_map = get_authority_map()

    def process_query_run(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        synthesized_answer: str,
        trace_id: Optional[str] = None,
        canonical_concept_id: Optional[str] = None,
        semantic_scope: str = "general",
    ) -> Tuple[RetrievalRunRecord, List[Dict[str, Any]]]:
        query_clean = query.strip()
        qid = f"query_{stable_hash({'q': query_clean})[:12]}"
        tid = trace_id or f"trace_{stable_hash({'q': query_clean, 'u': uuid.uuid4().hex})[:16]}"
        run_id = f"run_{stable_hash({'t': tid, 'q': qid})[:12]}"

        raw_candidate_count = len(candidates)
        deduped_candidates, selected_items = self._process_candidates(candidates)
        dedup_count = len(selected_items)

        # Build claim bindings for answer
        claim_bindings, overall_status = self._bind_claims_to_evidence(
            query=query_clean,
            answer=synthesized_answer,
            selected_items=selected_items,
        )

        replay_payload = {
            "query_id": qid,
            "trace_id": tid,
            "concept_id": canonical_concept_id or "general",
            "selected_evidence_hashes": [e.provenance_hash for e in selected_items],
            "claim_binding_hashes": [c.provenance_hash for c in claim_bindings],
            "status": overall_status,
        }
        replay_id = f"replay_{stable_hash(replay_payload)[:16]}"

        record = RetrievalRunRecord(
            query_id=qid,
            trace_id=tid,
            canonical_concept_id=canonical_concept_id or "unclassified",
            semantic_scope=semantic_scope,
            retrieval_run_id=run_id,
            index_version=INDEX_VERSION,
            candidate_count=raw_candidate_count,
            deduplicated_candidate_count=dedup_count,
            selected_evidence=selected_items,
            claim_bindings=claim_bindings,
            verification_status=overall_status,
            replay_id=replay_id,
            replay_safe=True,
        )

        return record, deduped_candidates

    def _process_candidates(
        self, candidates: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[RetrievedEvidenceItem]]:
        seen_hashes: set = set()
        deduped: List[Dict[str, Any]] = []
        items: List[RetrievedEvidenceItem] = []

        for cand in candidates:
            text = str(cand.get("content") or cand.get("text_span") or cand.get("clean_content") or "").strip()
            source = str(cand.get("source") or cand.get("source_id") or "MASTERDB").strip()
            concept = str(cand.get("concept") or cand.get("canonical_name") or "general").strip()

            # Determine authority tier
            tier_str = str(cand.get("authority_tier") or cand.get("source_type") or "CANONICAL").upper()
            if "MASTERDB" in source or "KOSHA" in source or "SANSKRIT" in source:
                tier = AuthorityTier.CANONICAL
            elif "FAISS" in source or "VECTOR" in source or "DERIVED" in tier_str:
                tier = AuthorityTier.DERIVED
            elif "FALLBACK" in tier_str or "LLM" in source:
                tier = AuthorityTier.FALLBACK
            elif "TEST" in tier_str:
                tier = AuthorityTier.TEST_FIXTURE
            else:
                tier = AuthorityTier.CANONICAL

            cobj = create_canonical_object(
                concept_id=concept,
                source_id=source,
                text_span=text,
                authority_tier=tier,
                domain=cand.get("domain"),
                tags=cand.get("tags", []),
            )

            # Deduplicate by concept + text content hash
            text_hash = stable_hash({"concept": concept, "text": text.lower()})
            is_duplicate = text_hash in seen_hashes
            dedup_status = "deduplicated_chunk" if is_duplicate else "unique"

            cand_copy = dict(cand)
            cand_copy["canonical_object_id"] = cobj.canonical_object_id
            cand_copy["provenance_hash"] = cobj.provenance_hash
            cand_copy["dedup_status"] = dedup_status
            cand_copy["authority_tier"] = tier.value

            if not is_duplicate and text:
                seen_hashes.add(text_hash)
                deduped.append(cand_copy)
                score = float(cand.get("confidence") or cand.get("score") or 0.85)
                items.append(
                    RetrievedEvidenceItem(
                        canonical_object_id=cobj.canonical_object_id,
                        source_id=source,
                        authority_tier=tier,
                        provenance_hash=cobj.provenance_hash,
                        ranking_score=score,
                        dedup_status=dedup_status,
                        text_span=text,
                        domain=cand.get("domain"),
                        tradition_context=cand.get("tradition", "general"),
                    )
                )

        return deduped, items

    def _bind_claims_to_evidence(
        self, query: str, answer: str, selected_items: List[RetrievedEvidenceItem]
    ) -> Tuple[List[ClaimEvidenceBinding], str]:
        if not selected_items or "I do not have verified knowledge" in answer:
            fallback_binding = ClaimEvidenceBinding(
                claim_id=f"claim_{stable_hash({'q': query, 'a': answer})[:12]}",
                claim_text=answer,
                canonical_object_id="uko:none:unverified",
                source_id="LLM_FALLBACK",
                text_span=answer,
                verification_status=ClaimVerificationStatus.UNVERIFIED_FALLBACK,
                confidence=0.0,
                provenance_hash=stable_hash({"unverified": True}),
            )
            return [fallback_binding], "NO_VERIFIED_KNOWLEDGE"

        # Split answer into sentence claims
        sentences = [s.strip() for s in re.split(r"[.!?]\s+", answer) if s.strip()]
        bindings: List[ClaimEvidenceBinding] = []
        overall_status = "VERIFIED"

        for idx, sentence in enumerate(sentences):
            sent_tokens = _clean_tokens(sentence)
            best_match: Optional[RetrievedEvidenceItem] = None
            best_overlap = 0

            for item in selected_items:
                item_tokens = _clean_tokens(item.text_span)
                overlap = len(sent_tokens & item_tokens)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_match = item

            cid = f"claim_{idx + 1}_{stable_hash({'s': sentence})[:8]}"
            if best_match and best_overlap > 0:
                if best_match.authority_tier == AuthorityTier.FALLBACK:
                    vstatus = ClaimVerificationStatus.UNVERIFIED_FALLBACK
                elif best_match.authority_tier == AuthorityTier.DERIVED:
                    vstatus = ClaimVerificationStatus.DERIVED
                else:
                    vstatus = ClaimVerificationStatus.VERIFIED

                binding = ClaimEvidenceBinding(
                    claim_id=cid,
                    claim_text=sentence,
                    canonical_object_id=best_match.canonical_object_id,
                    source_id=best_match.source_id,
                    text_span=best_match.text_span,
                    verification_status=vstatus,
                    confidence=best_match.ranking_score,
                    provenance_hash=best_match.provenance_hash,
                )
            else:
                overall_status = "PARTIAL_VERIFIED"
                binding = ClaimEvidenceBinding(
                    claim_id=cid,
                    claim_text=sentence,
                    canonical_object_id=selected_items[0].canonical_object_id,
                    source_id=selected_items[0].source_id,
                    text_span=selected_items[0].text_span,
                    verification_status=ClaimVerificationStatus.DERIVED,
                    confidence=0.5,
                    provenance_hash=selected_items[0].provenance_hash,
                )
            bindings.append(binding)

        return bindings, overall_status


def run_convergence_pipeline(
    query: str,
    candidates: List[Dict[str, Any]],
    synthesized_answer: str,
    trace_id: Optional[str] = None,
    canonical_concept_id: Optional[str] = None,
) -> Tuple[RetrievalRunRecord, List[Dict[str, Any]]]:
    runtime = KnowledgeConvergenceRuntime()
    return runtime.process_query_run(
        query=query,
        candidates=candidates,
        synthesized_answer=synthesized_answer,
        trace_id=trace_id,
        canonical_concept_id=canonical_concept_id,
    )
