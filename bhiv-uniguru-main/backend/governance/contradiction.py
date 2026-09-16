from __future__ import annotations

import re
from typing import Any, Dict, List


class ContradictionConsensusEngine:
    """Deterministic contradiction and consensus analysis for accepted signals."""

    NEGATION_PATTERNS = (
        r"\bnot\b",
        r"\bnever\b",
        r"\bno\b",
        r"\bwithout\b",
        r"\bdoes not\b",
        r"\bcannot\b",
    )
    AMBIGUITY_MARKERS = (
        "tradition",
        "interpretation",
        "appears",
        "may",
        "varies",
        "not provide a comprehensive",
    )

    @classmethod
    def analyze(cls, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not signals:
            return {
                "contradictions": [],
                "ambiguity_classification": "no_valid_signals",
                "consensus_score": 0.0,
                "contradiction_pressure": 0.0,
                "multi_source_reinforcement": 0.0,
                "disagreement_aware_synthesis": "No valid signals available.",
            }

        groups: Dict[str, List[Dict[str, Any]]] = {}
        for signal in signals:
            key = cls._claim_key(signal)
            groups.setdefault(key, []).append(signal)

        contradictions = []
        for key, grouped in groups.items():
            polarities = {cls._polarity(str(item.get("content") or "")) for item in grouped}
            if len(polarities) > 1:
                contradictions.append(
                    {
                        "claim_key": key,
                        "signal_ids": [str(item.get("signal_id")) for item in grouped],
                        "polarities": sorted(polarities),
                    }
                )

        sources = {str(signal.get("source") or "") for signal in signals if str(signal.get("source") or "").strip()}
        reinforcement = min(1.0, max(0.0, (len(sources) - 1) / 3.0))
        contradiction_pressure = min(1.0, len(contradictions) / max(len(groups), 1))
        consensus_score = round(max(0.0, reinforcement + 0.5 - contradiction_pressure), 4)
        ambiguity = cls._ambiguity(signals=signals, contradictions=contradictions)

        return {
            "contradictions": contradictions,
            "ambiguity_classification": ambiguity,
            "consensus_score": consensus_score,
            "contradiction_pressure": round(contradiction_pressure, 4),
            "multi_source_reinforcement": round(reinforcement, 4),
            "source_count": len(sources),
            "claim_group_count": len(groups),
            "disagreement_aware_synthesis": cls._synthesis_note(ambiguity, contradictions),
        }

    @classmethod
    def _polarity(cls, content: str) -> str:
        text = content.lower()
        if any(re.search(pattern, text) for pattern in cls.NEGATION_PATTERNS):
            return "negative"
        return "affirmative"

    @staticmethod
    def _claim_key(signal: Dict[str, Any]) -> str:
        validation = signal.get("_validation") or {}
        entities = validation.get("candidate_entities") or []
        if entities:
            return "|".join(sorted(str(entity.get("canonical")) for entity in entities[:3]))
        tags = signal.get("tags") or []
        if tags:
            return "|".join(sorted(str(tag).lower() for tag in tags[:3]))
        content = str(signal.get("content") or "").lower()
        terms = re.findall(r"[a-zA-Z0-9\u0900-\u097F]+", content)
        return "|".join(terms[:5]) or "unclassified_claim"

    @classmethod
    def _ambiguity(cls, *, signals: List[Dict[str, Any]], contradictions: List[Dict[str, Any]]) -> str:
        if contradictions:
            return "conflicting_claims"
        content = " ".join(str(signal.get("content") or "").lower() for signal in signals)
        if any(marker in content for marker in cls.AMBIGUITY_MARKERS):
            return "interpretive_or_weak_evidence_zone"
        if len({str(signal.get("source") or "") for signal in signals}) > 1:
            return "multi_source_consensus"
        return "single_source_verified"

    @staticmethod
    def _synthesis_note(ambiguity: str, contradictions: List[Dict[str, Any]]) -> str:
        if contradictions:
            return "Signals disagree; downstream synthesis must preserve disagreement."
        if ambiguity == "interpretive_or_weak_evidence_zone":
            return "Evidence is valid but interpretive or weak; do not flatten into universal certainty."
        return "No deterministic contradiction detected."
