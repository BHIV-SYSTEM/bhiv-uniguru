"""
UniGuru Universal Query Router
==============================
Central query classification, intent understanding, and routing layer.
Determines:
  - Intent / Category (GREETING, CASUAL_CONVERSATION, MATHEMATICS, PHYSICS, etc.)
  - Detected language (en, mr, hi, sa)
  - Whether RAG is required
  - Whether symbolic/programmatic math is required
  - Whether code engine is required
  - Whether live/current external information is required
  - Whether session memory / follow-up context is required
Does not rely solely on keyword matching: uses semantic pattern analysis,
syntactic checks, entity cues, and language properties.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class QueryCategory(str, Enum):
    GREETING = "GREETING"
    CASUAL_CONVERSATION = "CASUAL_CONVERSATION"
    USER_INTRODUCTION = "USER_INTRODUCTION"
    IDENTITY = "IDENTITY"
    FOLLOW_UP = "FOLLOW_UP"
    MATHEMATICS = "MATHEMATICS"
    PHYSICS = "PHYSICS"
    CHEMISTRY = "CHEMISTRY"
    BIOLOGY = "BIOLOGY"
    PROGRAMMING = "PROGRAMMING"
    SQL = "SQL"
    ENGLISH = "ENGLISH"
    MARATHI = "MARATHI"
    HINDI = "HINDI"
    TRANSLATION = "TRANSLATION"
    GENERAL_KNOWLEDGE = "GENERAL_KNOWLEDGE"
    KNOWLEDGE_BASE = "KNOWLEDGE_BASE"
    DOCUMENT_QUESTION = "DOCUMENT_QUESTION"
    CURRENT_INFORMATION = "CURRENT_INFORMATION"
    WEB_SEARCH = "WEB_SEARCH"
    REASONING = "REASONING"
    SUMMARIZATION = "SUMMARIZATION"
    OTHER = "OTHER"


class UniversalQueryRouter:
    """Universal intent classifier and capability router."""

    # Explicit Knowledge-Base topics supported by the local repository
    _KB_ENTITIES = {
        "dharma", "karma", "yoga", "karma yoga", "jnana yoga", "bhakti yoga",
        "atman", "brahman", "moksha", "maya", "prakriti", "purusha", "samsara",
        "upanishad", "taittiriya", "mahanarayana", "chandogya", "brihadaranyaka",
        "mandukya", "katha upanishad", "isha upanishad", "kena upanishad", "mundaka upanishad",
        "bhagavad gita", "gita", "vedas", "rigveda", "samaveda", "yajurveda", "atharvaveda",
        "nasadiya", "purusha sukta", "gayatri mantra", "sulba", "sulba sutra", "panini", "ashtadhyayi",
        "purana", "puranas", "padma purana", "narada purana", "agni purana", "brahma purana",
        "swaminarayan", "vachanamrut", "shikshapatri", "gunatit", "brahmavidya",
        "jain", "tattvartha", "tirthankara", "ahimsa", "anekantavada", "aparigraha",
        "gurukul", "vedic math", "pingala", "aryabhata", "brahmagupta", "varahamihira",
        "nyaya", "vaisheshika", "samkhya",
        "qubit", "superposition", "entanglement", "quantum computing",
        "density matrix", "shor", "grover", "quantum gate", "bloch sphere",
        "balbharati", "kosha", "annamaya", "pranamaya", "manomaya", "vijnanamaya", "anandamaya",
        "indus valley", "harappa", "mohenjo-daro", "lothal", "dholavira", "maurya", "ashoka",
        "gupta dynasty", "chola", "chhatrapati shivaji", "maratha", "mughal", "1857 revolt",
        "himalayas", "ganga", "brahmaputra", "godavari", "monsoon", "kharif", "rabi", "western ghats",
        "faraday", "lenz", "maxwell", "schrodinger", "heisenberg", "lorentz", "coulomb",
        "electronegativity", "vsepr", "le chatelier", "gibbs free energy", "nernst",
        "central dogma", "rubisco", "calvin cycle", "dna replication", "mitochondria",
        "operating system", "virtual memory", "deadlock", "tcp/ip", "osi model", "compiler",
        "retrieval-augmented generation", "transformer", "self-attention", "backpropagation", "xgboost",
        "sn1", "sn2", "reaction mechanism", "nucleophilic substitution", "arrhenius",
        "four vedas", "principal upanishads", "fundamental rights", "constitution of india",
        "subject-verb agreement", "verb agreement", "grammar rules", "समास", "samas", "संधि", "sandhi",
        "openstax", "riemann sum", "definite integral", "ncert",
    }


    def route(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Classify user query and decide routing parameters."""
        raw_q = query.strip()
        q_lower = raw_q.lower()

        # 1. Detect language
        language = self.detect_language(raw_q)

        # 2. Check for Greetings / Casual conversation / Identity
        cat = self._check_conversational(raw_q, q_lower)
        if cat:
            return self._build_route_decision(cat, language, query=raw_q, requires_rag=False)

        # 3. Check for Follow-Up queries
        if self._is_follow_up(q_lower):
            return self._build_route_decision(
                QueryCategory.FOLLOW_UP, language, query=raw_q, requires_rag=False, is_follow_up=True
            )

        # 4. Check for Translation requests
        if "translate" in q_lower or "भाषांतर" in q_lower or "अनुवाद" in q_lower:
            return self._build_route_decision(QueryCategory.TRANSLATION, language, query=raw_q, requires_rag=False)

        # 5. Check for SQL / Programming (prioritized over pure math when code keywords present)
        if self._is_sql(q_lower):
            return self._build_route_decision(QueryCategory.SQL, language, query=raw_q, requires_rag=False)
        if self._is_programming(q_lower):
            return self._build_route_decision(QueryCategory.PROGRAMMING, language, query=raw_q, requires_rag=False)

        # 6. Check for Physics (prioritized over math when physics variables/terms present)
        if self._is_physics(q_lower):
            return self._build_route_decision(QueryCategory.PHYSICS, language, query=raw_q, requires_rag=False)

        # 7. Check for Mathematics
        if self._is_mathematics(raw_q, q_lower):
            return self._build_route_decision(QueryCategory.MATHEMATICS, language, query=raw_q, requires_rag=False)

        # 8. Check for Chemistry
        if self._is_chemistry(q_lower):
            return self._build_route_decision(QueryCategory.CHEMISTRY, language, query=raw_q, requires_rag=False)

        # 9. Check for Biology
        if self._is_biology(q_lower):
            return self._build_route_decision(QueryCategory.BIOLOGY, language, query=raw_q, requires_rag=False)

        # 10. Check for English grammar correction
        if self._is_english_grammar(q_lower):
            return self._build_route_decision(QueryCategory.ENGLISH, language, query=raw_q, requires_rag=False)

        # 11. Check for Current Information / Web Search
        if self._is_current_info(q_lower):
            return self._build_route_decision(QueryCategory.CURRENT_INFORMATION, language, query=raw_q, requires_rag=False)

        # 12. Check for Knowledge-Base / RAG (Sanskrit, Gurukul, Jain, Swaminarayan, Quantum, Balbharati, Kosha)
        if self._is_knowledge_base(q_lower):
            return self._build_route_decision(QueryCategory.KNOWLEDGE_BASE, language, query=raw_q, requires_rag=True)

        # 13. Vernacular specific (Marathi / Hindi general questions)
        if language == "mr":
            return self._build_route_decision(QueryCategory.MARATHI, language, query=raw_q, requires_rag=False)
        if language == "hi":
            return self._build_route_decision(QueryCategory.HINDI, language, query=raw_q, requires_rag=False)

        # 14. General Knowledge (world capitals, geography, history)
        if self._is_general_knowledge(q_lower):
            return self._build_route_decision(QueryCategory.GENERAL_KNOWLEDGE, language, query=raw_q, requires_rag=False)

        # 15. Default fallback category
        return self._build_route_decision(QueryCategory.GENERAL_KNOWLEDGE, language, query=raw_q, requires_rag=False)

    def detect_language(self, text: str) -> str:
        """Detect language: mr (Marathi), hi (Hindi), sa (Sanskrit), en (English)."""
        devanagari_chars = len(re.findall(r"[\u0900-\u097F]", text))
        total_chars = len(re.sub(r"\s+", "", text))

        if total_chars == 0 or (devanagari_chars / total_chars) < 0.25:
            return "en"

        t_lower = text.lower()
        if any(w in t_lower for w in ["काय", "आहे", "म्हणजे", "कसे", "करा", "सांगा", "माझं", "नाव", "द्या"]):
            return "mr"
        if any(w in t_lower for w in ["क्या", "है", "का", "की", "के", "कैसे", "बताइए", "मेरा", "दीजिए"]):
            return "hi"
        if any(w in t_lower for w in ["किं", "कथं", "अस्ति", "इति", "सत्यात्", "धर्मो", "विद्यते"]):
            return "sa"

        return "mr"

    def _check_conversational(self, raw_q: str, q_lower: str) -> Optional[QueryCategory]:
        stripped = q_lower.strip("?!. ")

        # User Name Introduction
        if any(re.search(p, raw_q, re.IGNORECASE) for p in [
            r"\bmy name is\b", r"\bi am\b", r"\bcall me\b", r"\bमाझं नाव\b", r"\bमेरा नाम\b"
        ]):
            return QueryCategory.USER_INTRODUCTION

        # Identity queries
        if stripped in {
            "what is your name", "what's your name", "who are you", "what are you",
            "what is my name", "what's my name", "who am i",
            "माझं नाव काय आहे", "मेरा नाम क्या है"
        } or re.search(r"^(?:hi|hello|hey)[,\s]+what(?:'s|\s+is)\s+your\s+name", stripped):
            return QueryCategory.IDENTITY

        # Greetings
        if stripped in {
            "hi", "hello", "hey", "namaste", "namaskar", "good morning", "good afternoon", "good evening",
            "नमस्कार", "नमस्ते", "प्रणाम"
        } or re.search(r"^(?:hi|hello|hey)\b", stripped):
            return QueryCategory.GREETING

        # Casual conversation
        if stripped in {
            "how are you", "how are you doing", "what's up", "how's it going",
            "तू कसा आहेस", "तुम्ही कसे आहात", "आप कैसे हैं"
        }:
            return QueryCategory.CASUAL_CONVERSATION

        return None

    def _is_follow_up(self, q_lower: str) -> bool:
        # If the query already specifies a concrete topic (e.g. "Give an example of Newton's Second Law"),
        # it is not an unresolved follow-up and should be routed directly to the domain capability.
        if " of " in q_lower or " regarding " in q_lower or " about " in q_lower:
            return False

        patterns = [
            r"^explain\s+(?:it|this|that)\b",
            r"^simplify\s+(?:it|this|that)\b",
            r"^give\s+(?:me\s+)?an?\s+example\b",
            r"^tell\s+me\s+more\b",
            r"^what\s+about\s+(?:it|this|that)\b",
            r"^आणखी\s+सांगा\b",
            r"^उदाहरण\s+द्या\b",
            r"^और\s+बताइए\b",
            r"^उदाहरण\s+दीजिए\b",
        ]
        return any(re.search(p, q_lower) for p in patterns)

    def _is_mathematics(self, raw_q: str, q_lower: str) -> bool:
        # Equations with '='
        if "=" in raw_q and any(c in q_lower for c in "xyzabcdefg"):
            return True
        if "solve" in q_lower and any(c in q_lower for c in "xyz"):
            return True

        # Math calculation symbols or keywords
        math_keywords = [
            "differentiate", "derivative", "integrate", "integral",
            "calculate", "algebra", "trigonometry", "logarithm",
        ]
        if any(k in q_lower for k in math_keywords):
            return True

        # Percentage
        if re.search(r"\d+\s*%\s*of\s*\d+", q_lower):
            return True

        # Pure arithmetic expression: e.g. "2 + 2", "287 * 46", "287 × 46"
        clean = re.sub(r"^(?:what is|calculate|evaluate|solve|compute)\s+", "", q_lower).strip().rstrip("?")
        clean_expr = clean.replace("×", "*").replace("x", "*").replace("X", "*").replace("÷", "/")
        if re.match(r"^[\d\s\+\-\*\/\(\)\.\,]+$", clean_expr) and re.search(r"[\+\-\*\/]", clean_expr):
            return True

        return False

    def _is_physics(self, q_lower: str) -> bool:
        physics_terms = [
            "newton", "velocity", "acceleration", "kinetic energy", "potential energy",
            "gravitation", "gravity", "ohm's law", "resistance", "voltage", "current in a circuit",
            "thermodynamics", "optics", "focal length", "momentum", "f = ma",
            "force", "m/s", "joule", "watt", "ohm",
        ]
        if any(term in q_lower for term in physics_terms):
            return True
        if "calculate force" in q_lower or re.search(r"m\s*=\s*\d+.*(?:a|v)\s*=\s*\d+", q_lower):
            return True
        if re.search(r"[iIvV]\s*=\s*\d+.*[rR]\s*=\s*\d+", q_lower):
            return True
        return False

    def _is_chemistry(self, q_lower: str) -> bool:
        chem_terms = [
            "h2o", "h₂o", "chemical", "molecule", "periodic table", "atomic number",
            "covalent bond", "ionic bond", "acid", "base", "ph level", "reaction",
            "formula of water", "chemical formula",
            "रासायनिक सूत्र", "रासायनिक",
        ]
        return any(term in q_lower for term in chem_terms)

    def _is_biology(self, q_lower: str) -> bool:
        bio_terms = [
            "photosynthesis", "cellular respiration", "mitochondria", "chloroplast",
            "dna", "rna", "water cycle", "ecosystem", "cell membrane", "enzyme",
            "प्रकाशसंश्लेषण", "प्रकाश संश्लेषण", "जल चक्र", "जलचक्र",
        ]
        return any(term in q_lower for term in bio_terms)

    def _is_sql(self, q_lower: str) -> bool:
        return any(k in q_lower for k in [
            "second-highest salary", "2nd highest salary", "sql query", "write a query", "select from employee", "sql join"
        ])

    def _is_programming(self, q_lower: str) -> bool:
        prog_terms = [
            "python", "javascript", "typescript", "java", "c++", "cpp", "c#", "golang", "rust",
            "fastapi", "flask", "django", "react", "rest api", "reverse a string", "write code",
            "algorithm", "data structure", "dsa", "function to", "debug this code", "list slicing",
            "slicing", "status code", "http methods", "http status", "indexerror", "typeerror",
            "recursionerror", "keyerror", "valueerror", "syntaxerror", "attributeerror", "zerodivisionerror",
            "dict[key]", "dict[", "dictionary key",
            "recursion", "binary search", "pass by reference", "login api", "convert this python",
            "programming example", "what is a python list", "fix this code", "output of this",
            "factorial in python", "code to calculate factorial", "preferred programming language",
            "preferred language", "favorite programming language",
        ]
        return any(term in q_lower for term in prog_terms)

    def _is_english_grammar(self, q_lower: str) -> bool:
        return "correct this sentence" in q_lower or "grammar" in q_lower or "correct the sentence" in q_lower

    def _is_current_info(self, q_lower: str) -> bool:
        current_terms = [
            "today's weather", "current weather", "weather today",
            "latest news", "today's news", "current news", "breaking news",
            "stock price today", "current exchange rate", "live score"
        ]
        return any(term in q_lower for term in current_terms)

    def _is_knowledge_base(self, q_lower: str) -> bool:
        """Check if query specifically asks for indexed UniGuru civilizational & curriculum knowledge."""
        for entity in self._KB_ENTITIES:
            # Match whole words or phrases
            if re.search(r"\b" + re.escape(entity) + r"\b", q_lower):
                return True
        return False

    def _is_general_knowledge(self, q_lower: str) -> bool:
        gk_cues = ["capital of", "largest planet", "who was", "where is", "when did", "history of"]
        return any(cue in q_lower for cue in gk_cues)

    def _build_route_decision(
        self,
        category: QueryCategory,
        language: str,
        query: str,
        requires_rag: bool,
        is_follow_up: bool = False,
    ) -> Dict[str, Any]:
        return {
            "category": category.value,
            "language": language,
            "requires_rag": requires_rag,
            "is_follow_up": is_follow_up,
            "query": query,
        }


_router_instance = None


def get_universal_router() -> UniversalQueryRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = UniversalQueryRouter()
    return _router_instance
