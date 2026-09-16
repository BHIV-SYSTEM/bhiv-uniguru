from __future__ import annotations

from typing import Any, Dict
import uuid


def build_provenance(source: str = "canonical-registry") -> Dict[str, Any]:
    trace_id = str(uuid.uuid4())
    return {
        "source": source,
        "trace_id": trace_id,
        "replay_id": f"replay-{trace_id[:8]}",
    }


def build_replay_contract(provenance: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "replay_safe": True,
        "provenance": provenance,
        "version_policy": "immutable-trace",
    }
