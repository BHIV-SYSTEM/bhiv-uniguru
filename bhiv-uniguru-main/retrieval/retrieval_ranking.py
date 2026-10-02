from __future__ import annotations

from typing import Any, Dict, List


def rank_matches(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(matches, key=lambda row: row.get("score", 0.0), reverse=True)
