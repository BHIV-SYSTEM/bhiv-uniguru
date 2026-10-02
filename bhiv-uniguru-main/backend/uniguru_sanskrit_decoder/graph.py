from __future__ import annotations

from typing import Any, Dict, List


def build_knowledge_graph(pipeline: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "nodes": [step["stage"] for step in pipeline],
        "edges": [
            {"from": pipeline[index]["stage"], "to": pipeline[index + 1]["stage"]}
            for index in range(len(pipeline) - 1)
        ],
    }
