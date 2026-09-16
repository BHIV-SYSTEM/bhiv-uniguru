"""Evidence-Grounded Answer Synthesis with Citations and Multiple Answer Modes for Balbharati."""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("uniguru.balbharati.synthesizer")

CONFIDENCE_THRESHOLD = float(os.getenv("UNIGURU_BALBHARATI_CONFIDENCE_THRESHOLD", "0.35"))
INSUFFICIENT_EVIDENCE_MSG = "I could not find sufficient evidence in the selected Balbharati textbook."


def format_citation(item: Dict[str, Any]) -> str:
    std = item.get("standard", "?")
    subj = item.get("subject", "General")
    chap = item.get("chapter", "General")
    page = item.get("page", "?")
    med = item.get("medium", "English")
    book = item.get("book") or f"Standard {std} {subj}"
    return f"Source: Balbharati | Standard: {std} | Subject: {subj} | Book: {book} | Chapter: {chap} | Page: {page} | Medium: {med}"


class BalbharatiAnswerSynthesizer:
    def __init__(self, confidence_threshold: float = CONFIDENCE_THRESHOLD) -> None:
        self.confidence_threshold = confidence_threshold

    def synthesize(
        self,
        query: str,
        retrieval_result: Dict[str, Any],
        mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        results = retrieval_result.get("results", [])
        confidence = float(retrieval_result.get("confidence", 0.0))
        detected_meta = retrieval_result.get("detected_metadata", {})
        active_mode = mode or detected_meta.get("mode", "explain")

        # Insufficient evidence gate
        if not results or confidence < self.confidence_threshold:
            return {
                "answer": INSUFFICIENT_EVIDENCE_MSG,
                "confidence": confidence,
                "verification_status": "NO_VERIFIED_KNOWLEDGE",
                "citations": [],
                "evidence_chunks": [],
                "mode": active_mode,
            }

        top_chunks = results[:3]
        citations = [format_citation(r) for r in top_chunks]

        # Extract textual bodies from chunks (stripping the [header] tag for synthesis)
        body_snippets = []
        for r in top_chunks:
            text = r.get("text", "")
            clean = re.sub(r"^\[Book:.*?\]\n*", "", text, flags=re.MULTILINE).strip()
            if clean:
                body_snippets.append(clean)

        combined_evidence = "\n\n".join(body_snippets)

        # Synthesize according to mode
        answer_text = ""
        if active_mode == "definition":
            # Find definition sentences
            def_lines = [l for l in combined_evidence.splitlines() if any(k in l.lower() for k in ["is defined", "means", "म्हणजे", "म्हणतात", "व्याख्या", "अर्थ"])]
            if def_lines:
                answer_text = def_lines[0].strip()
            else:
                answer_text = body_snippets[0][:400].strip() if body_snippets else combined_evidence[:400]
        elif active_mode == "summary":
            # Extract key declarative points
            points = [s.strip() for s in re.split(r"(?<=[.!?।])\s+", combined_evidence) if len(s.strip()) > 20]
            selected_pts = points[:5]
            bullet_points = "\n".join(f"• {pt}" for pt in selected_pts)
            answer_text = f"Summary according to Balbharati Standard {top_chunks[0].get('standard')} {top_chunks[0].get('subject')}:\n\n{bullet_points}"
        elif active_mode == "qa":
            answer_text = f"According to Balbharati textbook (Page {top_chunks[0].get('page')}):\n\n{body_snippets[0]}"
        elif active_mode == "exam_prep":
            # Look for exercises or key definitions
            ex_chunks = [r.get("text", "") for r in results if r.get("content_type") == "exercise"]
            if ex_chunks:
                answer_text = f"Important questions from Chapter '{top_chunks[0].get('chapter')}':\n\n" + "\n\n".join(ex_chunks[:2])
            else:
                answer_text = f"Key concepts and exercise reference from Chapter '{top_chunks[0].get('chapter')}':\n\n{body_snippets[0]}"
        elif active_mode == "compare":
            answer_text = f"Comparison based on Balbharati curriculum evidence:\n\n{combined_evidence[:800]}"
        else:
            # Default "explain" mode
            answer_text = body_snippets[0] if len(body_snippets) == 1 else f"{body_snippets[0]}\n\n{body_snippets[1]}"

        # Append source citation
        primary_citation = citations[0]
        full_response = f"{answer_text}\n\n---\n{primary_citation}"

        return {
            "answer": full_response,
            "body": answer_text,
            "primary_citation": primary_citation,
            "citations": citations,
            "confidence": confidence,
            "verification_status": "VERIFIED",
            "evidence_chunks": top_chunks,
            "mode": active_mode,
            "detected_metadata": detected_meta,
            "available": True,
        }


_SYNTHESIZER_INSTANCE: Optional[BalbharatiAnswerSynthesizer] = None


def get_answer_synthesizer() -> BalbharatiAnswerSynthesizer:
    global _SYNTHESIZER_INSTANCE
    if _SYNTHESIZER_INSTANCE is None:
        _SYNTHESIZER_INSTANCE = BalbharatiAnswerSynthesizer()
    return _SYNTHESIZER_INSTANCE


format_attribution_citation = format_citation


def synthesize_balbharati_answer(
    retrieval_result: Dict[str, Any],
    query: str = "",
    mode: Optional[str] = None,
) -> Dict[str, Any]:
    synth = get_answer_synthesizer()
    q = query or retrieval_result.get("query", "")
    res = synth.synthesize(query=q, retrieval_result=retrieval_result, mode=mode)
    res["available"] = res.get("verification_status") == "VERIFIED"
    return res

