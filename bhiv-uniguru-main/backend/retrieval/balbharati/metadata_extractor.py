"""Query metadata extraction and intent classification for Maharashtra Balbharati curriculum."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BalbharatiQueryMetadata:
    standard: Optional[int] = None
    subject: Optional[str] = None
    medium: Optional[str] = None
    board: str = "Maharashtra"
    chapter: Optional[str] = None
    topic: Optional[str] = None
    mode: str = "explain"  # explain | qa | summary | definition | exam_prep | compare
    detected_language: str = "en"  # en | mr | hi
    clean_query: str = ""
    raw_query: str = ""

    def to_filter_dict(self) -> Dict[str, Any]:
        filters: Dict[str, Any] = {}
        if self.standard is not None:
            filters["standard"] = self.standard
        if self.subject:
            filters["subject"] = self.subject
        if self.medium:
            filters["medium"] = self.medium
        if self.chapter:
            filters["chapter"] = self.chapter
        return filters


_MARATHI_CLASS_MAP = {
    "पहिली": 1, "पहिला": 1, "१ली": 1, "१ ली": 1, "इयत्ता १": 1, "इयत्ता १ली": 1,
    "दुसरी": 2, "दुसरा": 2, "२री": 2, "२ री": 2, "इयत्ता २": 2, "इयत्ता २री": 2,
    "तिसरी": 3, "तिसरा": 3, "३री": 3, "३ री": 3, "इयत्ता ३": 3, "इयत्ता ३री": 3,
    "चौथी": 4, "चौथा": 4, "४थी": 4, "४ थी": 4, "इयत्ता ४": 4, "इयत्ता ४थी": 4,
    "पाचवी": 5, "पाचवा": 5, "५वी": 5, "५ वी": 5, "इयत्ता ५": 5, "इयत्ता ५वी": 5,
    "सहावी": 6, "सहावा": 6, "६वी": 6, "६ वी": 6, "इयत्ता ६": 6, "इयत्ता ६वी": 6,
    "सातवी": 7, "सातवा": 7, "७वी": 7, "७ वी": 7, "इयत्ता ७": 7, "इयत्ता ७वी": 7,
    "आठवी": 8, "आठवा": 8, "८वी": 8, "८ वी": 8, "इयत्ता ८": 8, "इयत्ता ८वी": 8,
    "नववी": 9, "नववा": 9, "९वी": 9, "९ वी": 9, "इयत्ता ९": 9, "इयत्ता ९वी": 9,
    "दहावी": 10, "दहावा": 10, "१०वी": 10, "१० वी": 10, "इयत्ता १०": 10, "इयत्ता १०वी": 10,
    "अकरावी": 11, "अकरावा": 11, "११वी": 11, "११ वी": 11, "इयत्ता ११": 11, "इयत्ता ११वी": 11,
    "बारावी": 12, "बारावा": 12, "१२वी": 12, "१२ वी": 12, "इयत्ता १२": 12, "इयत्ता १२वी": 12,
}

_HINDI_CLASS_MAP = {
    "कक्षा 1": 1, "कक्षा १": 1, "पहली कक्षा": 1,
    "कक्षा 2": 2, "कक्षा २": 2, "दूसरी कक्षा": 2,
    "कक्षा 3": 3, "कक्षा ३": 3, "तीसरी कक्षा": 3,
    "कक्षा 4": 4, "कक्षा ४": 4, "चौथी कक्षा": 4,
    "कक्षा 5": 5, "कक्षा ५": 5, "पांचवी कक्षा": 5, "पाँचवीं कक्षा": 5,
    "कक्षा 6": 6, "कक्षा ६": 6, "छठी कक्षा": 6, "छठवीं कक्षा": 6,
    "कक्षा 7": 7, "कक्षा ७": 7, "सातवीं कक्षा": 7,
    "कक्षा 8": 8, "कक्षा ८": 8, "आठवीं कक्षा": 8,
    "कक्षा 9": 9, "कक्षा ९": 9, "नौवीं कक्षा": 9,
    "कक्षा 10": 10, "कक्षा १०": 10, "दसवीं कक्षा": 10,
    "कक्षा 11": 11, "कक्षा ११": 11, "ग्यारहवीं कक्षा": 11,
    "कक्षा 12": 12, "कक्षा १२": 12, "बारहवीं कक्षा": 12,
}

_ROMAN_NUMERALS = {
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6,
    "vii": 7, "viii": 8, "ix": 9, "x": 10, "xi": 11, "xii": 12
}

_WORD_NUMBERS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
    "eleventh": 11, "twelfth": 12,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12,
}

_SUBJECT_KEYWORDS = [
    ("Science", [
        "science", "general science", "physics", "chemistry", "biology",
        "विज्ञान", "सामान्य विज्ञान", "भौतिकशास्त्र", "रसायनशास्त्र", "जीवशास्त्र",
        "evs", "environmental studies", "परिसर अभ्यास", "पर्यावरण अध्ययन"
    ]),
    ("Mathematics", [
        "mathematics", "math", "maths", "algebra", "geometry", "arithmetic",
        "गणित", "बीजगणित", "भूमिती", "अंकगणित"
    ]),
    ("History", [
        "history", "इतिहास", "history and civics", "इतिहास आणि नागरिकशास्त्र",
        "प्राचीन इतिहास", "मध्ययुगीन इतिहास", "आधुनिक इतिहास"
    ]),
    ("Geography", [
        "geography", "भूगोल", "भूगोलाचा", "भूगोलशास्त्र"
    ]),
    ("Civics", [
        "civics", "political science", "नागरिकशास्त्र", "राज्यशास्त्र"
    ]),
    ("English", [
        "english", "english balbharati", "kumarbharati", "yuvakbharati", "my english book",
        "इंग्रजी"
    ]),
    ("Marathi", [
        "marathi", "मराठी", "मराठी बालभारती", "अक्षरभारती", "सुगमभारती"
    ]),
    ("Hindi", [
        "hindi", "हिंदी", "हिंदी बालभारती", "लोकभारती", "सुगमभारती"
    ]),
]

_CROSS_LINGUAL_ACADEMIC_TERMS: Dict[str, str] = {
    # Biology / Living World
    "प्रकाशसंश्लेषण": "photosynthesis",
    "प्रकाश संश्लेषण": "photosynthesis",
    "अन्नसाखळी": "food chain",
    "अन्नजाळे": "food web",
    "सजीव": "living things",
    "सजीवांची लक्षणे": "characteristics of living things",
    "सजीवांचे वर्गीकरण": "classification of living things",
    "वनस्पती रचना व कार्य": "plants structure and function",
    "वनस्पतींमधील पोषण": "nutrition in plants",
    "प्राण्यांमधील पोषण": "nutrition in animals",
    "पेशी": "cell",
    "पेशीरचना": "cell structure",
    "सूक्ष्मजीव": "microorganisms",
    "समतोल आहार": "balanced diet",
    "पोषण": "nutrition",
    "पचनसंस्था": "digestive system",
    "श्वसन": "respiration",
    "रक्ताभिसरण": "circulation",
    "उत्सर्जन": "excretion",
    "प्रजनन": "reproduction",
    "वनस्पती": "plants",
    "प्राणी": "animals",
    # Physics / Chemistry
    "गुरुत्वाकर्षण": "gravitation gravity",
    "गती": "motion",
    "गतीचे नियम": "laws of motion",
    "बल": "force",
    "कार्य आणि ऊर्जा": "work and energy",
    "ऊर्जा": "energy",
    "ऊर्जेचे स्रोत": "sources of energy",
    "उष्णता": "heat",
    "प्रकाश": "light",
    "ध्वनी": "sound",
    "विद्युत": "electricity",
    "विद्युतधारा": "electric current",
    "चुंबकत्व": "magnetism",
    "द्रव्य": "matter",
    "अणू": "atom",
    "अणूची संरचना": "atomic structure",
    "मूलद्रव्ये": "elements",
    "संयुगे": "compounds",
    "मिश्रणे": "mixtures",
    "आम्ल": "acid",
    "आम्लारी": "base alkali",
    "क्षार": "salt",
    "रासायनिक अभिक्रिया": "chemical reactions",
    # Environment / Geography
    "पर्यावरण": "environment",
    "पर्यावरण व्यवस्थापन": "environmental management",
    "नैसर्गिक संसाधने": "natural resources",
    "हवामान": "weather climate",
    "जलचक्र": "water cycle",
    "आपत्ती व्यवस्थापन": "disaster management",
    "प्रदूषण": "pollution",
    "हवा प्रदूषण": "air pollution",
    "जल प्रदूषण": "water pollution",
    "मृदा": "soil",
    # Mathematics
    "संख्याज्ञान": "number system",
    "पूर्णांक संख्या": "integers",
    "अपूर्णांक": "fractions",
    "लसावि": "lcm",
    "मसावि": "hcf gcf",
    "गुणोत्तर व प्रमाण": "ratio and proportion",
    "शेकडेवारी": "percentage",
    "नफा तोटा": "profit and loss",
    "सरळव्याज": "simple interest",
    "समीकरणे": "equations",
    "त्रिकोण": "triangle",
    "चौकोन": "quadrilateral",
    "वर्तुळ": "circle",
    "क्षेत्रफळ": "area",
    "घनफळ": "volume",
    "भूमिती": "geometry",
    "सांख्यिकी": "statistics",
    # Hindi terms
    "खाद्य श्रृंखला": "food chain",
    "गति": "motion",
    "कोशिका": "cell",
    "जल चक्र": "water cycle",
    "परमाणु": "atom",
}


def _expand_cross_lingual_terms(text: str) -> List[str]:
    expansions = []
    norm = text.lower()
    for term, target in _CROSS_LINGUAL_ACADEMIC_TERMS.items():
        if term in text or term in norm:
            expansions.append(target)
    return expansions



def _detect_language(text: str) -> str:
    devanagari_chars = len(re.findall(r"[\u0900-\u097F]", text))
    if devanagari_chars > 2:
        marathi_markers = ["आहे", "नाही", "सांग", "पुस्तकातील", "इयत्ता", "विज्ञान", "विषय", "करा", "स्पष्ट", "च्या"]
        for marker in marathi_markers:
            if marker in text:
                return "mr"
        hindi_markers = ["है", "नहीं", "बताओ", "पुस्तक", "कक्षा", "की", "का", "क्या", "में"]
        for marker in hindi_markers:
            if marker in text:
                return "hi"
        return "mr"
    return "en"


def _extract_standard(text: str) -> Optional[int]:
    lower = text.lower()

    # Marathi patterns
    for pattern, std in _MARATHI_CLASS_MAP.items():
        if pattern in text:
            return std

    # Hindi patterns
    for pattern, std in _HINDI_CLASS_MAP.items():
        if pattern in text:
            return std

    # Regex patterns for English: "class 7", "standard 7", "std 7", "grade 7", "7th std", "7th class"
    m = re.search(r"\b(?:class|standard|std|grade)\s*[:\-]?\s*(\d{1,2})\b", lower)
    if m:
        val = int(m.group(1))
        if 1 <= val <= 12:
            return val

    m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s*(?:standard|class|grade|std)\b", lower)
    if m:
        val = int(m.group(1))
        if 1 <= val <= 12:
            return val

    # Roman numerals: "class vii", "std ix"
    m = re.search(r"\b(?:class|standard|std|grade)\s+([ivx]{1,4})\b", lower)
    if m and m.group(1) in _ROMAN_NUMERALS:
        return _ROMAN_NUMERALS[m.group(1)]

    # Words: "fifth standard", "class seven"
    for word, std in _WORD_NUMBERS.items():
        if re.search(rf"\b{word}\s+(?:standard|class|grade|std)\b", lower) or re.search(rf"\b(?:class|standard|std|grade)\s+{word}\b", lower):
            return std

    return None


def _extract_medium(text: str, default_lang: str) -> Optional[str]:
    lower = text.lower()
    if any(k in lower for k in ["marathi medium", "मराठी माध्यम", "in marathi", "मराठीतून", "मराठीत"]):
        return "Marathi"
    if any(k in lower for k in ["english medium", "इंग्रजी माध्यम", "in english", "इंग्रजीत"]):
        return "English"
    if any(k in lower for k in ["hindi medium", "हिंदी माध्यम", "in hindi", "हिंदीत"]):
        return "Hindi"

    # If query is heavily Devanagari Marathi and asks for balbharati, prefer Marathi medium
    if default_lang == "mr" and any(k in text for k in ["पुस्तकातील", "समजावून", "सांग", "पाचवीच्या", "इयत्ता"]):
        return "Marathi"
    if default_lang == "hi" and any(k in text for k in ["पुस्तक", "में", "क्या", "बताओ"]):
        return "Hindi"

    return None


def _extract_subject(text: str) -> Optional[str]:
    lower = text.lower()
    for subject, keywords in _SUBJECT_KEYWORDS:
        for kw in keywords:
            # Word boundary check or substring for devanagari
            if re.search(rf"\b{re.escape(kw)}\b", lower) or kw in text:
                return subject
    return None


def _extract_chapter(text: str) -> Optional[str]:
    # e.g., "Chapter 4", "Chapter: Our Environment", "धडा ४", "प्रकरण ५"
    m = re.search(r"\b(?:chapter|lesson|unit|धडा|प्रकरण)\s*[:\-]?\s*([A-Za-z0-9\u0900-\u097F\s\-]{2,30})", text, re.IGNORECASE)
    if m:
        ch = m.group(1).strip()
        # Clean trailing stopwords
        ch = re.sub(r"\b(?:in|of|according|to|from)\b.*$", "", ch, flags=re.IGNORECASE).strip()
        if ch:
            return ch
    return None


def _extract_mode(text: str) -> str:
    lower = text.lower()

    if any(k in lower for k in ["compare", "difference between", "distinguish", "तुलना", "फरक"]):
        return "compare"
    if any(k in lower for k in ["important question", "exam preparation", "exam question", "test", "महत्वाचे प्रश्न", "परीक्षेचे प्रश्न"]):
        return "exam_prep"
    if any(k in lower for k in ["summarize", "summary", "सारांश", "थोडक्यात सांग"]):
        return "summary"
    if any(k in lower for k in ["what is", "define", "definition", "व्याख्या", "म्हणजे काय", "का अर्थ"]):
        return "definition"
    if any(k in lower for k in ["exercise", "question 3", "q3", "स्वाध्याय", "प्रश्न ३", "answer question", "solve"]):
        return "qa"

    return "explain"


def extract_balbharati_metadata(query: str) -> BalbharatiQueryMetadata:
    """Analyze query and extract Balbharati curriculum filters and intent."""
    norm_query = unicodedata.normalize("NFC", str(query or "").strip())
    detected_lang = _detect_language(norm_query)
    standard = _extract_standard(norm_query)
    medium = _extract_medium(norm_query, detected_lang)
    subject = _extract_subject(norm_query)
    chapter = _extract_chapter(norm_query)
    mode = _extract_mode(norm_query)

    # Clean query for search keywords by removing explicit standard / board mentions
    clean = re.sub(r"\b(?:class|standard|std|grade)\s*\d{1,2}(?:st|nd|rd|th)?\b", " ", norm_query, flags=re.IGNORECASE)
    clean = re.sub(r"\b(?:maharashtra|balbharati|state board)\b", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"इयत्ता\s*\d{1,2}(?:वी|ली|री|थी)?", " ", clean)
    clean = re.sub(r"कक्षा\s*\d{1,2}", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()

    # Cross-lingual expansion for Marathi/Hindi academic terms
    expansions = _expand_cross_lingual_terms(norm_query)
    search_query = clean or norm_query
    if expansions:
        search_query = f"{search_query} {' '.join(expansions)}"
        # If subject was not detected from raw keywords, check if expansions infer it
        if not subject:
            subject = _extract_subject(search_query)

    return BalbharatiQueryMetadata(
        standard=standard,
        subject=subject,
        medium=medium,
        board="Maharashtra",
        chapter=chapter,
        topic=clean,
        mode=mode,
        detected_language=detected_lang,
        clean_query=search_query,
        raw_query=norm_query,
    )

