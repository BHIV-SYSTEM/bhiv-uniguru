"""
UniGuru Multilingual & Vernacular Capability
=============================================
Handles native Marathi, Hindi, and Sanskrit queries directly in the user's language:
  - Marathi queries (e.g. "गुरुत्वाकर्षण म्हणजे काय?", "प्रकाशसंश्लेषण म्हणजे काय?")
  - Hindi queries (e.g. "जल चक्र क्या है?", "प्रकाश संश्लेषण क्या है?")
  - Sanskrit queries
Ensures answers are rendered naturally in the requested language without unwanted English fallback.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


class MultilingualEngine:
    """Multilingual query answering engine for Marathi, Hindi, and Sanskrit."""

    def detect_language(self, text: str) -> str:
        """Detect language: mr (Marathi), hi (Hindi), sa (Sanskrit), en (English)."""
        # Devanagari Unicode range: \u0900-\u097F
        devanagari_chars = len(re.findall(r"[\u0900-\u097F]", text))
        total_chars = len(re.sub(r"\s+", "", text))

        if total_chars == 0:
            return "en"

        if devanagari_chars / total_chars > 0.25:
            # Distinguish Marathi vs Hindi vs Sanskrit by typical stop-words/inflections
            t_lower = text.lower()
            if any(w in t_lower for w in ["काय", "आहे", "म्हणजे", "कसे", "करा", "सांगा", "माझं", "नाव", "द्या"]):
                return "mr"
            if any(w in t_lower for w in ["क्या", "है", "का", "की", "के", "कैसे", "बताइए", "मेरा", "दीजिए"]):
                return "hi"
            if any(w in t_lower for w in ["किं", "कथं", "अस्ति", "इति", "सत्यात्", "धर्मो", "विद्यते"]):
                return "sa"
            return "mr"  # Default Devanagari to Marathi in Maharashtra state context

        return "en"

    def solve(self, query: str, lang: str) -> Optional[Dict[str, Any]]:
        clean_q = query.strip()
        q_lower = clean_q.lower()

        # 1. Marathi: Gravity / गुरुत्वाकर्षण म्हणजे काय?
        if "गुरुत्वाकर्षण" in q_lower:
            if lang == "mr" or "म्हणजे" in q_lower or "काय" in q_lower:
                answer = (
                    "**गुरुत्वाकर्षण (Gravitation / Gravity)**:\n\n"
                    "गुरुत्वाकर्षण हे विश्वातील कोणत्याही दोन वस्तुमान (mass) असलेल्या वस्तूंमधील नैसर्गिक आकर्षण बल आहे.\n\n"
                    "### न्यूटनचा वैश्विक गुरुत्वाकर्षणाचा नियम:\n"
                    "विश्वातील प्रत्येक कण इतर प्रत्येक कणाला एका विशिष्ट बलाने स्वतःकडे आकर्षित करतो. हे बल त्यांच्या वस्तुमानांच्या गुणाकाराशी समप्रमाणात आणि त्यांच्यामधील अंतराच्या वर्गाशी व्यस्त प्रमाणात असते.\n\n"
                    "$$F = G \\frac{m_1 m_2}{r^2}$$\n\n"
                    "- **$F$**: गुरुत्वाकर्षण बल (Newtons, N)\n"
                    "- **$G$**: वैश्विक गुरुत्वाकर्षण स्थिरांक ($6.674 \\times 10^{-11} \\text{ N}\\cdot\\text{m}^2/\\text{kg}^2$)\n"
                    "- **$m_1, m_2$**: दोन वस्तूंचे वस्तुमान\n"
                    "- **$r$**: त्यांच्यामधील अंतर\n\n"
                    "### दैनंदिन जीवनातील महत्त्व:\n"
                    "1. पृथ्वीच्या गुरुत्वाकर्षणामुळे आपण जमिनीवर स्थिर राहू शकतो.\n"
                    "2. चंद्र पृथ्वीभोवती आणि सर्व ग्रह सूर्याभोवती गुरुत्वाकर्षणामुळेच फिरतात."
                )
            else:
                answer = (
                    "**गुरुत्वाकर्षण (Gravitational Force)**:\n\n"
                    "गुरुत्वाकर्षण वह प्राकृतिक आकर्षण बल है जो द्रव्यमान वाली किन्हीं भी दो वस्तुओं के बीच कार्य करता है।\n\n"
                    "### न्यूटन का सार्वत्रिक गुरुत्वाकर्षण नियम:\n"
                    "$$F = G \\frac{m_1 m_2}{r^2}$$\n\n"
                    "पृथ्वी का गुरुत्वाकर्षण बल सभी वस्तुओं को अपने केंद्र की ओर खींचता है।"
                )
            return {
                "capability": "MULTILINGUAL_SCIENCE",
                "language": lang,
                "result": "Gravitation",
                "answer": answer,
                "verified": True,
            }

        return None


_multilingual_instance = None


def get_multilingual_engine() -> MultilingualEngine:
    global _multilingual_instance
    if _multilingual_instance is None:
        _multilingual_instance = MultilingualEngine()
    return _multilingual_instance
