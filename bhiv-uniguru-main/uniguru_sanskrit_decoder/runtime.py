from __future__ import annotations

from typing import Any, Dict

from .decoder import decode_sanskrit_concept
from .governance import build_replay_contract


class DecoderRuntime:
    def __init__(self) -> None:
        self.name = "UniGuru Sanskrit Decoder Runtime"

    def execute(self, concept: str) -> Dict[str, Any]:
        result = decode_sanskrit_concept(concept)
        replay_contract = build_replay_contract(result["provenance"])
        return {
            "canonical_concept": result["canonical_concept"],
            "pipeline": result["pipeline"],
            "replay_safe": replay_contract["replay_safe"],
            "execution_metadata": {
                "replay_id": replay_contract["provenance"]["replay_id"],
                "observability": "enabled",
                "runtime": self.name,
            },
            "knowledge_graph": result["knowledge_graph"],
        }
