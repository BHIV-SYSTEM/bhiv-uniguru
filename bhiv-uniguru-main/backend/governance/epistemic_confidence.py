from __future__ import annotations

from typing import Any, Dict, List


class EpistemicConfidenceEngine:
    """Truth-likelihood confidence, separate from retrieval match strength."""

    @classmethod
    def derive(
        cls,
        *,
        retrieval_confidence: float,
        validation_details: Dict[str, Any],
        source_governance: Dict[str, Any],
        consensus: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        consensus = consensus or {}
        semantic_score = float(validation_details.get("semantic_score") or 0.0)
        domain_consistency = float(validation_details.get("domain_consistency") or 0.0)
        contextual_consistency = max(
            float(validation_details.get("content_overlap") or 0.0),
            float(validation_details.get("contextual_proximity") or 0.0),
        )
        source_authority = float(source_governance.get("authority_weight") or 0.0)
        ocr_integrity = max(0.0, 1.0 - float(source_governance.get("ocr_integrity_penalty") or 0.0))
        semantic_agreement = max(
            float(validation_details.get("concept_overlap") or 0.0),
            float(validation_details.get("entity_overlap") or 0.0),
        )
        contradiction_pressure = float(consensus.get("contradiction_pressure") or 0.0)
        multi_source_reinforcement = float(consensus.get("multi_source_reinforcement") or 0.0)
        ontology_convergence = (semantic_score + domain_consistency + semantic_agreement) / 3.0

        raw = (
            0.22 * source_authority
            + 0.18 * semantic_agreement
            + 0.16 * ontology_convergence
            + 0.14 * contextual_consistency
            + 0.12 * ocr_integrity
            + 0.10 * multi_source_reinforcement
            + 0.08 * float(retrieval_confidence)
            - 0.26 * contradiction_pressure
        )
        ceiling = min(float(source_governance.get("confidence_ceiling") or 0.5), cls._convergence_ceiling(validation_details))
        score = round(max(0.0, min(raw, ceiling)), 4)
        return {
            "score": score,
            "confidence_ceiling": round(ceiling, 4),
            "dimensions": {
                "source_authority": round(source_authority, 4),
                "semantic_agreement": round(semantic_agreement, 4),
                "contradiction_pressure": round(contradiction_pressure, 4),
                "contextual_consistency": round(contextual_consistency, 4),
                "ontology_convergence": round(ontology_convergence, 4),
                "ocr_integrity": round(ocr_integrity, 4),
                "multi_source_reinforcement": round(multi_source_reinforcement, 4),
                "retrieval_strength": round(float(retrieval_confidence), 4),
            },
            "formula": (
                "0.22*source_authority + 0.18*semantic_agreement + "
                "0.16*ontology_convergence + 0.14*contextual_consistency + "
                "0.12*ocr_integrity + 0.10*multi_source_reinforcement + "
                "0.08*retrieval_strength - 0.26*contradiction_pressure, capped by source/convergence ceilings"
            ),
            "why": cls._why(score=score, ceiling=ceiling, source_governance=source_governance),
        }

    @staticmethod
    def _convergence_ceiling(validation_details: Dict[str, Any]) -> float:
        if float(validation_details.get("domain_consistency") or 0.0) < 1.0:
            return 0.62
        if float(validation_details.get("semantic_score") or 0.0) < 0.45:
            return 0.78
        return 0.95

    @staticmethod
    def _why(score: float, ceiling: float, source_governance: Dict[str, Any]) -> List[str]:
        reasons = [
            f"epistemic_score={score:.4f}",
            f"ceiling_applied={ceiling:.4f}",
            f"source_type={source_governance.get('source_type', 'unknown')}",
        ]
        suppression = source_governance.get("suppression_reason")
        if suppression:
            reasons.append(str(suppression))
        return reasons
