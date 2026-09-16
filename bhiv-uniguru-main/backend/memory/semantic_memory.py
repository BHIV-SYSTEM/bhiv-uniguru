from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .constitutional_semantic_memory import (
    ConstitutionalSemanticMemory,
    build_pipeline_memory_request,
)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_PATH = ROOT / "review_packets" / "proof_logs" / "semantic_memory_state.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class SemanticMemoryStore:
    """Observable, replayable semantic continuity store.

    This is not chat history. It only records trace-linked semantic continuity,
    unresolved threads, reinforcement, contradiction pressure, and decay state.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or DEFAULT_STATE_PATH

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {
                "schema": "UNIGURU_SEMANTIC_MEMORY_V1",
                "updated_at": None,
                "users": {},
                "entities": {},
                "unresolved_threads": {},
                "events": [],
            }
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {
                "schema": "UNIGURU_SEMANTIC_MEMORY_V1",
                "updated_at": None,
                "users": {},
                "entities": {},
                "unresolved_threads": {},
                "events": [],
                "load_warning": "Previous memory state was unreadable; started observable empty state.",
            }

    def update_from_pipeline(
        self,
        *,
        trace_id: str,
        user_id: str,
        query: str,
        accepted_signals: List[Dict[str, Any]],
        rejected_signals: List[Dict[str, Any]],
        consensus: Dict[str, Any],
        verification_status: str,
        retrieval_truth_hash: Optional[str] = None,
        interpretation_hash: Optional[str] = None,
        truth_interpretation_link: Optional[Dict[str, Any]] = None,
        confidence: float = 0.0,
        ontology_lineage: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        constitutional_result = ConstitutionalSemanticMemory().record_pipeline_mutation(
            build_pipeline_memory_request(
                trace_id=trace_id,
                user_id=user_id,
                query=query,
                accepted_signals=accepted_signals,
                rejected_signals=rejected_signals,
                consensus=consensus,
                verification_status=verification_status,
                retrieval_truth_hash=retrieval_truth_hash,
                interpretation_hash=interpretation_hash,
                truth_interpretation_link=truth_interpretation_link,
                confidence=confidence,
                ontology_lineage=ontology_lineage,
            )
        )

        state = self.load()
        now = _utc_now_iso()
        user_key = user_id or "anonymous"
        user_state = state.setdefault("users", {}).setdefault(
            user_key,
            {"trace_ids": [], "queries": 0, "last_seen": None, "continuity_score": 0.0},
        )
        user_state["queries"] = int(user_state.get("queries", 0)) + 1
        user_state["last_seen"] = now
        if trace_id not in user_state.setdefault("trace_ids", []):
            user_state["trace_ids"].append(trace_id)
        user_state["trace_ids"] = user_state["trace_ids"][-50:]
        user_state["continuity_score"] = round(min(1.0, 0.1 + len(user_state["trace_ids"]) / 20), 4)

        touched_entities: List[str] = []
        contradiction_pressure = float(consensus.get("contradiction_pressure") or 0.0)
        for signal in accepted_signals:
            validation = signal.get("_validation") or {}
            entities = validation.get("candidate_entities") or []
            for entity in entities:
                canonical = str(entity.get("canonical") or "").strip()
                if not canonical:
                    continue
                touched_entities.append(canonical)
                entity_state = state.setdefault("entities", {}).setdefault(
                    canonical,
                    {
                        "trace_ids": [],
                        "source_ids": [],
                        "reinforcement_score": 0.0,
                        "contradiction_pressure": 0.0,
                        "decay_state": "active",
                        "last_seen": None,
                    },
                )
                if trace_id not in entity_state.setdefault("trace_ids", []):
                    entity_state["trace_ids"].append(trace_id)
                source_id = str(signal.get("source") or "").strip()
                if source_id and source_id not in entity_state.setdefault("source_ids", []):
                    entity_state["source_ids"].append(source_id)
                entity_state["last_seen"] = now
                entity_state["contradiction_pressure"] = round(
                    max(float(entity_state.get("contradiction_pressure") or 0.0), contradiction_pressure),
                    4,
                )
                source_factor = min(1.0, len(entity_state.get("source_ids", [])) / 4)
                trace_factor = min(1.0, len(entity_state.get("trace_ids", [])) / 8)
                contradiction_penalty = entity_state["contradiction_pressure"] * 0.35
                entity_state["reinforcement_score"] = round(max(0.0, source_factor * 0.5 + trace_factor * 0.5 - contradiction_penalty), 4)
                entity_state["decay_state"] = "active" if entity_state["reinforcement_score"] >= 0.2 else "weak"

        unresolved_key = f"{user_key}:{trace_id}"
        if verification_status != "VERIFIED" or rejected_signals or contradiction_pressure > 0:
            state.setdefault("unresolved_threads", {})[unresolved_key] = {
                "trace_id": trace_id,
                "user_id": user_key,
                "query": query,
                "verification_status": verification_status,
                "rejected_signal_count": len(rejected_signals),
                "contradiction_pressure": contradiction_pressure,
                "state": "open",
                "updated_at": now,
            }

        event = {
            "event": "semantic_memory_update",
            "trace_id": trace_id,
            "user_id": user_key,
            "entities_touched": sorted(set(touched_entities)),
            "unresolved_thread_opened": unresolved_key in state.get("unresolved_threads", {}),
            "contradiction_pressure": contradiction_pressure,
            "constitutional_event_hash": constitutional_result["event_hash"],
            "memory_classification": constitutional_result["governance_decision"]["memory_classification"],
            "canonical_authority_granted": constitutional_result["governance_decision"]["canonical_authority_granted"],
            "updated_at": now,
        }
        state.setdefault("events", []).append(event)
        state["events"] = state["events"][-200:]
        state["updated_at"] = now
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(state, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")
        return {
            "schema": state["schema"],
            "state_path": str(self.path.as_posix()),
            "event": event,
            "user_continuity": user_state,
            "entity_continuity": {
                key: state.get("entities", {}).get(key)
                for key in sorted(set(touched_entities))
            },
            "unresolved_threads": [
                thread
                for thread in state.get("unresolved_threads", {}).values()
                if thread.get("trace_id") == trace_id
            ],
            "constitutional_governance": constitutional_result,
            "observable": True,
            "replayable": True,
            "canonical_authority_granted": constitutional_result["governance_decision"]["canonical_authority_granted"],
        }
