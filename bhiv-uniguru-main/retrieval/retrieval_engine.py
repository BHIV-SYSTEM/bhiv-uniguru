from __future__ import annotations

import json
import os
import re
import sys
import importlib.util
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

_curr = Path(__file__).resolve()
ROOT = _curr.parents[1]
for _p in [_curr.parent, _curr.parents[1], _curr.parents[2] if len(_curr.parents) > 2 else _curr.parents[1]]:
    if (_p / "masterdb").is_dir() and (_p / "retrieval").is_dir():
        ROOT = _p
        break
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.memory.constitutional_semantic_memory import stable_hash

# Canonical dataset — synthetic records are excluded from this path
MASTERDB_PATH = ROOT / "masterdb" / "balbharti" / "canonical_dataset.json"
EVIDENCE_FIRST_RETRIEVAL_PATH = ROOT / "retrieval" / "evidence_first_retrieval.py"

# Deterministic retrieval acceptance gates.
# Both conditions must pass before a curriculum record is considered relevant.
MIN_SEMANTIC_OVERLAP = float(
    os.getenv("UNIGURU_MIN_SEMANTIC_OVERLAP", "0.35")
)
MIN_ACCEPTANCE_SCORE = float(
    os.getenv("UNIGURU_MIN_ACCEPTANCE_SCORE", "0.45")
)

def _load_evidence_builder():
    spec = importlib.util.spec_from_file_location(
        "_uniguru_evidence_first_retrieval",
        str(EVIDENCE_FIRST_RETRIEVAL_PATH),
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load evidence builder from {EVIDENCE_FIRST_RETRIEVAL_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.build_evidence_handle


build_evidence_handle = _load_evidence_builder()


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()

STOPWORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "was",
    "were",
    "what",
    "which",
    "who",
    "when",
    "where",
    "why",
    "how",
    "explain",
    "tell",
    "about",
    "for",
    "to",
    "in",
    "on",
    "of",
    "and",
    "or",
    "me",
    "please",
    "can",
    "could",
    "would",
    "should",
}

def _tokens(text: str) -> set:
    tokens: set = set()

    for token in _normalize(text).split():
        if not token or token in STOPWORDS:
            continue

        tokens.add(token)

        if token.endswith("ies") and len(token) > 3:
            tokens.add(f"{token[:-3]}y")
        elif token.endswith("s") and len(token) > 3:
            tokens.add(token[:-1])

    return tokens

def load_masterdb_records() -> List[Dict[str, Any]]:
    if not MASTERDB_PATH.exists():
        return []
    loaded = json.loads(MASTERDB_PATH.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, list) else []


def _score_record(
    query: str,
    record: Dict[str, Any],
    grade: Optional[int] = None,
    medium: Optional[str] = None,
    subject: Optional[str] = None,
) -> float:
    query_tokens = _tokens(query)

    if not query_tokens:
        return 0.0

    fields = [
        record.get("chapter"),
        record.get("concept"),
        record.get("definition"),
        record.get("learning_outcome"),
        " ".join(record.get("examples") or []),
        " ".join(record.get("questions") or []),
    ]

    record_tokens = _tokens(
        " ".join(str(field or "") for field in fields)
    )

    overlap = len(query_tokens & record_tokens) / max(len(query_tokens), 1)

    concept_match = bool(
        record.get("concept")
        and _normalize(record.get("concept")) in _normalize(query)
    )

    chapter_match = bool(
        record.get("chapter")
        and _normalize(record.get("chapter")) in _normalize(query)
    )

    # Semantic relevance is the primary signal.
    score = overlap

    if chapter_match:
        score += 0.15

    if concept_match:
        score += 0.20

    # Metadata is compatibility only.
    # It must never dominate semantic relevance.
    if grade is not None and int(record.get("grade") or 0) == int(grade):
        score += 0.05

    if medium and str(record.get("medium") or "").lower() == str(medium).lower():
        score += 0.03

    if subject and str(record.get("subject") or "").lower() == str(subject).lower():
        score += 0.05

    if record.get("difficulty") == "easy" and "easy" in query.lower():
        score += 0.02

    if record.get("difficulty") == "hard" and "hard" in query.lower():
        score += 0.02

    return round(min(score, 1.0), 4)


def _related_score(record: Dict[str, Any], reference: Dict[str, Any]) -> float:
    if not reference or not record:
        return 0.0

    score = 0.0
    if record.get("subject") == reference.get("subject"):
        score += 0.25
    if record.get("chapter") == reference.get("chapter"):
        score += 0.3
    if int(record.get("grade") or 0) == int(reference.get("grade") or 0):
        score += 0.1
    if abs(int(record.get("grade") or 0) - int(reference.get("grade") or 0)) == 1:
        score += 0.12
    score += len(
        _tokens(str(record.get("concept") or "")) & _tokens(str(reference.get("concept") or ""))
    ) * 0.02
    return round(min(score, 1.0), 4)


def build_curriculum_graph(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not records:
        return {"nodes": [], "edges": []}

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    for record in records:
        nodes.append(
            {
                "id": record.get("record_id"),
                "concept": record.get("concept"),
                "chapter": record.get("chapter"),
                "subject": record.get("subject"),
                "grade": record.get("grade"),
                "medium": record.get("medium"),
                "difficulty": record.get("difficulty"),
                "learning_outcome": record.get("learning_outcome"),
            }
        )

    subject_records: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        subject_records[record.get("subject")].append(record)

    for subject, rows in subject_records.items():
        ordered = sorted(
            rows, key=lambda row: (int(row.get("grade") or 0), str(row.get("chapter") or ""))
        )
        for previous, current in zip(ordered, ordered[1:]):
            if previous.get("grade") and current.get("grade"):
                edges.append(
                    {
                        "from": previous.get("record_id"),
                        "to": current.get("record_id"),
                        "type": "grade_progression",
                        "subject": subject,
                    }
                )

    for record in records:
        for candidate in records:
            if record is candidate:
                continue
            if (
                record.get("chapter") == candidate.get("chapter")
                and record.get("record_id") != candidate.get("record_id")
            ):
                edges.append(
                    {
                        "from": record.get("record_id"),
                        "to": candidate.get("record_id"),
                        "type": "chapter_cluster",
                        "subject": record.get("subject"),
                    }
                )
                if len(edges) > 5000:
                    break
        if len(edges) > 5000:
            break

    return {"nodes": nodes, "edges": edges}

def _is_relevant_match(
    query: str,
    record: Dict[str, Any],
    score: float,
) -> bool:
    query_tokens = _tokens(query)

    if not query_tokens:
        return False

    semantic_fields = [
        record.get("chapter"),
        record.get("concept"),
        record.get("definition"),
        record.get("learning_outcome"),
        " ".join(record.get("examples") or []),
        " ".join(record.get("questions") or []),
    ]

    record_tokens = _tokens(
        " ".join(str(field or "") for field in semantic_fields)
    )

    semantic_overlap = (
        len(query_tokens & record_tokens)
        / max(len(query_tokens), 1)
    )

    concept_match = bool(
        record.get("concept")
        and _normalize(record.get("concept")) in _normalize(query)
    )

    chapter_match = bool(
        record.get("chapter")
        and _normalize(record.get("chapter")) in _normalize(query)
    )

    # Explicit concept/chapter matches are strong evidence.
    if concept_match or chapter_match:
        return score >= 0.35

    # Otherwise require meaningful semantic overlap.
    return (
        semantic_overlap >= MIN_SEMANTIC_OVERLAP
        and score >= MIN_ACCEPTANCE_SCORE
    )

def find_top_matches(
    query: str,
    grade: Optional[int] = None,
    medium: Optional[str] = None,
    subject: Optional[str] = None,
    max_results: int = 5,
) -> Dict[str, Any]:
    records = load_masterdb_records()
    candidate_records = [
        record
        for record in records
        if (grade is None or int(record.get("grade") or 0) == grade)
        and (medium is None or str(record.get("medium") or "").lower() == str(medium).lower())
        and (subject is None or str(record.get("subject") or "").lower() == str(subject).lower())
    ]
    if not candidate_records:
        candidate_records = records

    scored = [
        {
            "record": record,
            "score": _score_record(query, record, grade=grade, medium=medium, subject=subject),
        }
        for record in candidate_records
    ]
    scored = [
    row
    for row in scored
    if _is_relevant_match(
        query=query,
        record=row["record"],
        score=row["score"],
    )
]
    scored.sort(key=lambda row: row["score"], reverse=True)
    matches = scored[:max_results]
    best_record = matches[0]["record"] if matches else None

    related_records = (
        sorted(
            [
                {
                    "record": candidate,
                    "score": _related_score(candidate, best_record),
                }
                for candidate in records
                if candidate.get("record_id") != (best_record or {}).get("record_id")
            ],
            key=lambda row: row["score"],
            reverse=True,
        )[:max_results]
        if best_record
        else []
    )
    related_records = [row["record"] for row in related_records if row["score"] > 0]

    # Inject immutable evidence handles into every matched record
    for item in matches:
        rec = item["record"]
        rec["evidence"] = build_evidence_handle(rec, query, item["score"]).to_dict()

    if best_record:
        confidence = min(matches[0]["score"], 1.0) if matches else 0.0
        best_record["evidence"] = build_evidence_handle(best_record, query, confidence).to_dict()

    for rec in related_records:
        rec["evidence"] = build_evidence_handle(rec, query, 0.5).to_dict()

    curriculum_graph = build_curriculum_graph(records)
    chapter_recommendations: List[Any] = []
    if best_record:
        chapter_recommendations = [best_record.get("chapter")]
        for candidate in related_records:
            if candidate.get("chapter") not in chapter_recommendations:
                chapter_recommendations.append(candidate.get("chapter"))

    return {
        "matches": matches,
        "best_record": best_record,
        "confidence": min(matches[0]["score"], 1.0) if matches else 0.0,
        "related_records": related_records,
        "chapter_recommendations": chapter_recommendations,
        "learning_objectives": [best_record.get("learning_outcome")] if best_record else [],
        "curriculum_graph": curriculum_graph,
        "retrieval_hash": stable_hash(matches),
        "dataset_path": str(MASTERDB_PATH.relative_to(ROOT).as_posix()),
    }


def retrieve_from_masterdb(
    query: str,
    grade: Optional[int] = None,
    medium: Optional[str] = None,
    subject: Optional[str] = None,
) -> Dict[str, Any]:
    return find_top_matches(query=query, grade=grade, medium=medium, subject=subject)


def generate_retrieval_artifact(
    query: str,
    grade: Optional[int] = None,
    medium: Optional[str] = None,
    subject: Optional[str] = None,
) -> Dict[str, Any]:
    retrieval = retrieve_from_masterdb(query=query, grade=grade, medium=medium, subject=subject)
    record = retrieval.get("best_record") or {}
    return {
        "trace_id": stable_hash(
            {"query": query, "grade": grade, "medium": medium, "subject": subject}
        )[:16],
        "query": query,
        "grade": grade,
        "medium": medium,
        "subject": subject,
        "retrieved_record_id": record.get("record_id"),
        "retrieved_concepts": [record.get("concept")] if record else [],
        "curriculum_version": record.get("curriculum_version"),
        "version": record.get("version"),
        "knowledge_hash": stable_hash(record) if record else None,
        "source_lineage": record.get("source_lineage"),
        "evidence": record.get("evidence"),
        "confidence_state": {
            "confidence": retrieval.get("confidence", 0.0),
            "matched_chapter": record.get("chapter"),
            "matched_subject": record.get("subject"),
        },
        "matched_record": record,
        "related_records": [r.get("record_id") for r in retrieval.get("related_records", [])],
        "chapter_recommendations": retrieval.get("chapter_recommendations", []),
        "learning_objectives": retrieval.get("learning_objectives", []),
        "retrieval_hash": retrieval.get("retrieval_hash"),
        "dataset_path": retrieval.get("dataset_path"),
    }
