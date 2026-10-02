"""Canonical evidence contracts for the UniGuru retrieval boundary.

This module deliberately does not rank, chunk, or index content.  It turns the
output of a retriever into an immutable, replayable evidence record.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional
import hashlib
import json
import uuid


CONTRACT_VERSION = "UNIGURU_CANONICAL_EVIDENCE_V1"


class AuthorityStatus(str, Enum):
    CANONICAL = "CANONICAL"
    DERIVED = "DERIVED"
    FALLBACK = "FALLBACK"
    TEST_FIXTURE = "TEST_FIXTURE"
    LEGACY = "LEGACY"


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _id(namespace: str, value: Any) -> str:
    return f"{namespace}_{uuid.uuid5(uuid.NAMESPACE_URL, stable_hash(value)).hex}"


@dataclass(frozen=True)
class CanonicalKnowledgeObject:
    canonical_object_id: str
    canonical_concept_id: str
    ksml_identity: str
    source_id: str
    source_authority: str
    authority_status: str
    source_context: Dict[str, Any]
    text_reference: Dict[str, Any]
    provenance_hash: str
    schema_version: str
    knowledge_version: Optional[str]
    parent_object_id: Optional[str]
    graph_relationships: List[Dict[str, Any]]
    indexed_version: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def canonical_object_from_record(record: Dict[str, Any]) -> CanonicalKnowledgeObject:
    """Adapt an existing MasterDB record; do not mint an independent knowledge store."""
    lineage = record.get("source_lineage") or {}
    record_id = str(record.get("record_id") or _id("masterdb_record", record))
    concept = str(record.get("concept") or record_id)
    source_id = str(lineage.get("textbook_id") or record.get("textbook_id") or "MASTERDB")
    knowledge_version = record.get("version") or record.get("curriculum_version")
    text_ref = {
        "record_id": record_id,
        "chapter": record.get("chapter") or lineage.get("chapter"),
        "section": lineage.get("section"),
        "page": lineage.get("page"),
        "field": "definition",
    }
    provenance = {
        "source_id": source_id,
        "record_id": record_id,
        "source_hash": lineage.get("source_hash"),
        "text_reference": text_ref,
        "knowledge_version": knowledge_version,
    }
    return CanonicalKnowledgeObject(
        canonical_object_id=_id("cko", {"source_id": source_id, "record_id": record_id, "version": knowledge_version}),
        canonical_concept_id=record_id,
        ksml_identity=f"curriculum:{str(record.get('subject') or 'unknown').lower()}:{concept.lower().replace(' ', '_')}",
        source_id=source_id,
        source_authority="MASTERDB",
        authority_status=AuthorityStatus.CANONICAL.value,
        source_context={"publisher": lineage.get("publisher"), "board": lineage.get("board"), "medium": record.get("medium"), "grade": record.get("grade"), "subject": record.get("subject")},
        text_reference=text_ref,
        provenance_hash=stable_hash(provenance),
        schema_version=CONTRACT_VERSION,
        knowledge_version=str(knowledge_version) if knowledge_version is not None else None,
        parent_object_id=None,
        graph_relationships=[],
        indexed_version=None,
    )


def build_retrieval_run(query: str, retrieval: Dict[str, Any], *, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a deterministic evidence contract from candidates already ranked upstream."""
    raw_matches = list(retrieval.get("matches") or [])
    selected: List[Dict[str, Any]] = []
    seen: set[str] = set()
    duplicate_count = 0
    for position, candidate in enumerate(raw_matches, start=1):
        record = candidate.get("record") or candidate
        obj = canonical_object_from_record(record)
        if obj.canonical_object_id in seen:
            duplicate_count += 1
            continue
        seen.add(obj.canonical_object_id)
        selected.append({
            "canonical_object": obj.to_dict(),
            "canonical_object_id": obj.canonical_object_id,
            "source_id": obj.source_id,
            "source_authority": obj.source_authority,
            "source_context": obj.source_context,
            "provenance_hash": obj.provenance_hash,
            "ranking": {"rank": position, "retrieval_score": candidate.get("score"), "reranker": "not_configured"},
            "index": {"authority_status": AuthorityStatus.DERIVED.value, "index_version": retrieval.get("index_version") or "masterdb-direct-v1", "rebuild_from": retrieval.get("dataset_path")},
        })
    best = selected[0] if selected else None
    scope = {"authority_status": AuthorityStatus.CANONICAL.value, "allowed_sources": ["MASTERDB"], "filters": filters or {}}
    deterministic = {"query": query, "scope": scope, "selected_evidence": selected, "candidate_count": len(raw_matches), "retrieval_index_version": retrieval.get("index_version") or "masterdb-direct-v1"}
    run_id = _id("retrieval_run", deterministic)
    return {
        "schema_version": CONTRACT_VERSION,
        "query_id": _id("query", {"query": query, "filters": filters or {}}),
        "query": query,
        "canonical_concept_id": (best or {}).get("canonical_object", {}).get("canonical_concept_id"),
        "semantic_scope": scope,
        "retrieval_run_id": run_id,
        "retrieval_index_version": deterministic["retrieval_index_version"],
        "candidate_count": len(raw_matches),
        "deduplicated_candidate_count": len(selected),
        "duplicates_removed": duplicate_count,
        "selected_evidence": selected,
        "replay_id": _id("replay", deterministic),
        "replay_verification_status": "PENDING",
        "retrieval_run_hash": stable_hash(deterministic),
    }


def bind_answer_claims(answer: str, evidence_run: Dict[str, Any]) -> List[Dict[str, Any]]:
    """One generated answer is valid only when each substantive claim has evidence."""
    evidence = evidence_run.get("selected_evidence") or []
    if not answer or not evidence:
        return []
    first = evidence[0]
    claim_id = _id("claim", {"answer": answer, "evidence": first["canonical_object_id"]})
    return [{
        "claim_id": claim_id,
        "claim_text": answer,
        "claim_type": "answer_summary",
        "evidence_ids": [first["canonical_object_id"]],
        "provenance_hashes": [first["provenance_hash"]],
        "validation_status": "EVIDENCE_BOUND",
    }]


def verify_replay(query: str, retrieval: Dict[str, Any], expected_run: Dict[str, Any], *, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    replay = build_retrieval_run(query, retrieval, filters=filters)
    checks = {
        "retrieval_run_hash_stable": replay["retrieval_run_hash"] == expected_run.get("retrieval_run_hash"),
        "selected_evidence_stable": replay["selected_evidence"] == expected_run.get("selected_evidence"),
        "canonical_concept_stable": replay["canonical_concept_id"] == expected_run.get("canonical_concept_id"),
    }
    return {"replay_id": expected_run.get("replay_id"), "checks": checks, "replay_verified": all(checks.values()), "replay_run_hash": replay["retrieval_run_hash"]}
