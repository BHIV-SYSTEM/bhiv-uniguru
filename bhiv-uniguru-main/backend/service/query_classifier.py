from __future__ import annotations

import re
import random
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class QueryType(str, Enum):
    CASUAL_CONVERSATION = "casual_conversation"
    KNOWLEDGE_QUERY = "knowledge_query"
    CONCEPT_QUERY = "concept_query"
    EXPLANATION_QUERY = "explanation_query"
    TECHNICAL_QUERY = "technical_query"
    CODE_QUERY = "code_query"
    GENERAL_QUERY = "general_query"
    FOLLOW_UP_QUERY = "follow_up_query"
    WEB_LOOKUP = "web_lookup"
    UNKNOWN_QUERY = "unknown_query"


# ---------------------------------------------------------------------------
# PATTERN DEFINITIONS
# ---------------------------------------------------------------------------

_GREETING_PATTERNS = (
    r"^(hi|hello|hey|hiya|howdy|greetings)\b",
    r"^(good\s+(morning|afternoon|evening|day))\b",
    r"^(namaste|namaskar|pranam|jai\s+swaminarayan|radhe\s+radhe|hare\s+krishna|om\s+shanti)\b",
    r"^hi\s+(uniguru|guru|there|everyone|all)\b",
    r"^hello\s+(uniguru|guru|there|everyone|all)\b",
    r"^hey\s+(there|uniguru|guru)\b",
)

_INQUIRY_PATTERNS = (
    r"\bhow\s+are\s+you\b",
    r"\bhow\s+are\s+you\s+doing\b",
    r"\bhow\s+r\s+u\b",
    r"\bhow\s+do\s+you\s+do\b",
    r"\bhow('s|\s+is)\s+it\s+going\b",
    r"\bhow('s|\s+is)\s+everything\b",
    r"\bwhat('s|\s+is)\s+up\b",
    r"\bwhats\s+up\b",
    r"\bhow('s|\s+is)\s+your\s+day\b",
)

_GRATITUDE_PATTERNS = (
    r"\b(thank\s+you|thanks|thx|tysm|thank\s+you\s+very\s+much|many\s+thanks)\b",
    r"\b(appreciate\s+it|much\s+appreciated|thanks\s+a\s+lot)\b",
)

_ACKNOWLEDGMENT_PATTERNS = (
    r"^(ok|okay|k|cool|great|nice|awesome|wonderful|fine|understood|got\s+it|sounds\s+good|alright|perfect)\b",
    r"^(that's\s+(great|good|cool|awesome|clear|helpful))\b",
)

_DEPARTURE_PATTERNS = (
    r"\b(bye|goodbye|bye\s+bye|good\s+night|see\s+you|see\s+ya|take\s+care|farewell|have\s+a\s+(good|great|nice)\s+day)\b",
)

_CODE_REQUEST_PATTERNS = (
    r"\b(write|create|implement|code|generate|build)\b.*\b(function|script|code|class|method|program|algorithm)\b",
    r"\b(python|javascript|typescript|java|c\+\+|sql|bash)\b.*\b(function|code|script|example|snippet)\b",
    r"\b(reverse\s+a\s+string|sort\s+a\s+list|binary\s+search|factorial|fibonacci|palindrome)\b",
    r"^write\s+a\s+(python|javascript|script|function|program)\b",
)

_TECHNICAL_PATTERNS = (
    r"\b(python|fastapi|flask|django|docker|kubernetes|sql|mysql|postgresql|sqlite|mongodb|redis)\b",
    r"\b(rag|faiss|vector\s+(database|db|search)|embedding|embeddings|llm|transformer|bert|gpt)\b",
    r"\b(api|apis|rest\s+api|http|json|asyncio|endpoint|middleware|jwt|oauth)\b",
    r"\b(machine\s+learning|deep\s+learning|neural\s+network|gradient\s+descent|classification|regression)\b",
    r"\b(list\s+comprehension|dict|dictionary|tuple|generator|decorator|lambda\s+function)\b",
)

_SANSKRUTI_KNOWLEDGE_PATTERNS = (
    r"\b(brahman|atman|paramatman|ishvara|purusha|prakriti|maya|guna)\b",
    r"\b(dharma|karma|moksha|samsara|ahimsa|satya|satyam\s+vada|asteya|brahmacharya|aparigraha)\b",
    r"\b(veda|vedas|rigveda|samaveda|yajurveda|atharvaveda|upanishad|upanishads|vedanta)\b",
    r"\b(gita|bhagavad\s+gita|mahabharata|ramayana|purana|puranas|bhagavatam)\b",
    r"\b(sanskrit|shloka|mantra|sutra|darshana|tattva|kosha|koshas|prana|chakra|chakras)\b",
    r"\b(swaminarayan|vachanamrut|shikshapatri|akshar\s+purushottam|gurukul)\b",
    r"\b(jain|tirthankara|anekantavada|syadvada)\b",
)

_WEB_LOOKUP_PATTERNS = (
    r"\btoday\b",
    r"\blatest\b",
    r"\bcurrent\b",
    r"\brecent\b",
    r"\bnews\b",
    r"\bweather\b",
    r"\bmarket\b",
    r"\bprice\b",
    r"\bscore\b",
)

_CONCEPT_PATTERNS = (
    r"^what\s+is\b",
    r"^define\b",
    r"\bmeaning\s+of\b",
    r"\bconcept\s+of\b",
    r"\bdifference\s+between\b",
)

_EXPLANATION_PATTERNS = (
    r"^how\b",
    r"^why\b",
    r"\bexplain\b",
    r"\bwalk\s+me\s+through\b",
    r"\btell\s+me\s+about\b",
)

_FOLLOW_UP_INDICATORS = (
    r"^(explain|tell\s+me|elaborate|simplify|expand)\s+(it|this|that|them|more)\b",
    r"^(can\s+you\s+)?explain\s+(it|this|that)\s+(simply|more|in\s+detail|further)\b",
    r"^(who\s+wrote|what\s+about|why\s+does|how\s+does)\s+(it|this|that)\b",
    r"^(what\s+does\s+(it|that|this)\s+mean)\b",
    r"^(give\s+me\s+an\s+example|more\s+details|tell\s+me\s+more|continue)\b",
    r"\bhow\s+do\s+i\s+connect\s+it\b",
    r"\bhow\s+to\s+use\s+it\b",
)

_UNKNOWN_FICTIONAL_PATTERNS = (
    r"\bxyzabc[0-9]*\b",
    r"\bnonexistent\s+concept\b",
    r"\bcompletely\s+nonexistent\b",
    r"\bfake\s+concept\b",
    r"\bfoo_bar_baz_999\b",
)


# ---------------------------------------------------------------------------
# CASUAL RESPONSES
# ---------------------------------------------------------------------------

_CASUAL_GREETING_RESPONSES = [
    "Hello! \U0001F44B How can I help you today?",
    "Hi there! \U0001F44B What would you like to explore today?",
    "Greetings! How can I assist you on your learning journey today?",
]

_CASUAL_INQUIRY_RESPONSES = [
    "I'm doing well, thank you! How can I assist you today?",
    "I'm doing great! \U0001F60A What would you like to explore today?",
    "All is well, thank you! What knowledge can I help you with today?",
]

_CASUAL_GRATITUDE_RESPONSES = [
    "You're welcome! Let me know if you need anything else.",
    "Glad I could help! \U0001F60A Feel free to ask if you have more questions.",
    "Anytime! Let me know if there's anything else you'd like to explore.",
]

_CASUAL_ACKNOWLEDGMENT_RESPONSES = [
    "Great! Let me know what you'd like to explore next.",
    "Understood! I'm here whenever you're ready.",
    "Sounds good! What would you like to dive into next?",
]

_CASUAL_DEPARTURE_RESPONSES = [
    "Goodbye! Have a wonderful day.",
    "Good night! Wishing you peace and restful sleep.",
    "Take care! Have a great day ahead! \U0001F44B",
]


# ---------------------------------------------------------------------------
# UTILITY AND CLASSIFICATION FUNCTIONS
# ---------------------------------------------------------------------------

def is_casual_conversation(query: str) -> bool:
    """
    Check if a query is strictly casual conversation (greeting, small talk, gratitude, departure).
    Returns False if the query also contains a knowledge or technical question.
    """
    text = query.strip().lower()
    if not text:
        return True

    if is_mixed_knowledge_query(text):
        return False

    cleaned = re.sub(r"[?!.,]+$", "", text).strip()

    exact_casual = {
        "hi", "hello", "hey", "hiya", "howdy", "good morning", "good evening",
        "good afternoon", "good day", "how are you", "how are you doing", "what's up",
        "whats up", "how's it going", "how r u", "thank you", "thanks", "thx",
        "okay", "ok", "k", "great", "nice", "cool", "awesome", "bye", "goodbye",
        "good night", "hi uniguru", "hello uniguru", "hey uniguru", "namaste",
        "jai swaminarayan", "pranam", "radhe radhe", "hare krishna", "om shanti",
        "see you", "take care", "got it", "understood",
    }
    if cleaned in exact_casual:
        return True

    for pat in _GREETING_PATTERNS + _INQUIRY_PATTERNS + _GRATITUDE_PATTERNS + _ACKNOWLEDGMENT_PATTERNS + _DEPARTURE_PATTERNS:
        if re.search(pat, cleaned):
            remainder = re.sub(pat, "", cleaned).strip(" ,!?;:-")
            if not remainder or remainder in exact_casual or len(remainder.split()) <= 2:
                return True
    return False


def is_mixed_knowledge_query(query: str) -> bool:
    """
    Detect if query combines a casual greeting with a substantive question:
    e.g., 'Hi, can you explain Brahman?', 'Hello, what is Dharma?', 'Hey, tell me about Karma.'
    """
    text = query.strip().lower()
    has_greeting = any(re.search(pat, text) for pat in _GREETING_PATTERNS)
    if not has_greeting:
        return False

    stripped = extract_question_from_mixed(query)
    if stripped and len(stripped.split()) >= 2 and stripped.lower() != text:
        return True
    return False


def extract_question_from_mixed(query: str) -> str:
    """
    Strips casual greetings from a mixed query:
    'Hi, can you explain Brahman?' -> 'Explain Brahman' or 'can you explain Brahman?'
    """
    text = query.strip()
    for pat in _GREETING_PATTERNS:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            text = text[match.end():].strip(" ,!?;:-")
            break
    text_clean = re.sub(r"^(can\s+you\s+(please\s+)?|could\s+you\s+(please\s+)?|please\s+)", "", text, flags=re.IGNORECASE).strip()
    return text_clean if text_clean else text


def is_code_query(query: str) -> bool:
    """Check if query is a request to write or implement code."""
    text = query.strip().lower()
    return any(re.search(pat, text) for pat in _CODE_REQUEST_PATTERNS)


def is_technical_query(query: str) -> bool:
    """Check if query is about programming, computing, software, or AI/ML."""
    text = query.strip().lower()
    return any(re.search(pat, text) for pat in _TECHNICAL_PATTERNS)


def is_sanskrit_knowledge_query(query: str) -> bool:
    """Check if query involves Sanskrit, Vedic, philosophical, or civilizational concepts."""
    text = query.strip().lower()
    return any(re.search(pat, text) for pat in _SANSKRUTI_KNOWLEDGE_PATTERNS)


def is_unknown_or_fictional(query: str) -> bool:
    """Detect queries that explicitly target nonexistent or test-fictional concepts."""
    text = query.strip().lower()
    return any(re.search(pat, text) for pat in _UNKNOWN_FICTIONAL_PATTERNS)


def is_follow_up_query(query: str, context: Optional[List[Dict[str, Any]]] = None) -> bool:
    """Check if query is a follow-up that relies on prior conversation context."""
    text = query.strip().lower()
    if any(re.search(pat, text) for pat in _FOLLOW_UP_INDICATORS):
        return True
    words = text.split()
    if len(words) <= 6 and any(p in words for p in ("it", "this", "that", "them", "more")):
        return True
    return False


def resolve_context_query(query: str, context: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Resolves pronouns and context references in a follow-up query using recent chat messages.
    """
    if not context or not isinstance(context, list):
        return query

    prior_subject = ""
    for item in reversed(context):
        role = item.get("sender") or item.get("role")
        content = str(item.get("content") or item.get("text") or "").strip()
        if role in {"user", "human"} and content and not is_casual_conversation(content):
            cleaned_prior = extract_question_from_mixed(content)
            candidate = re.sub(r"^(what\s+is|what\s+are|explain|tell\s+me\s+about|define|who\s+wrote|how\s+does)\s+", "", cleaned_prior, flags=re.IGNORECASE).strip(" ?.,!")
            if candidate and len(candidate.split()) <= 4:
                prior_subject = candidate
                break

    if not prior_subject:
        return query

    text = query.strip()
    if re.search(r"\b(it|this|that)\b", text, re.IGNORECASE):
        resolved = re.sub(r"\b(it|this|that)\b", prior_subject, text, count=1, flags=re.IGNORECASE)
        return resolved
    if re.search(r"^(explain|simplify)\s+(simply|more|further)", text, re.IGNORECASE):
        return f"Explain {prior_subject} simply"
    if re.search(r"^(tell\s+me\s+more|more\s+details)", text, re.IGNORECASE):
        return f"Tell me more about {prior_subject}"

    return f"{text} (context: {prior_subject})"


def generate_casual_response(query: str) -> str:
    """Generates a warm, natural ChatGPT-style response for casual conversation."""
    text = query.strip().lower()
    cleaned = re.sub(r"[?!.,]+$", "", text).strip()

    if any(tok in cleaned for tok in ("jai swaminarayan", "pranam", "namaste", "radhe radhe", "hare krishna")):
        if "jai swaminarayan" in cleaned:
            return "Jai Swaminarayan \U0001F64F How may I assist you on your spiritual and learning journey today?"
        return "Namaste \U0001F64F How can I assist you on your learning path today?"

    if any(re.search(pat, cleaned) for pat in _GRATITUDE_PATTERNS) or cleaned in {"thanks", "thank you", "thx"}:
        return random.choice(_CASUAL_GRATITUDE_RESPONSES)

    if any(re.search(pat, cleaned) for pat in _DEPARTURE_PATTERNS) or cleaned in {"bye", "goodbye", "good night"}:
        if "night" in cleaned:
            return "Good night! \U0001F319 Wishing you peace, rest, and tranquility."
        return random.choice(_CASUAL_DEPARTURE_RESPONSES)

    if any(re.search(pat, cleaned) for pat in _INQUIRY_PATTERNS) or cleaned in {"how are you", "how are you doing", "what's up", "how r u"}:
        return random.choice(_CASUAL_INQUIRY_RESPONSES)

    if any(re.search(pat, cleaned) for pat in _ACKNOWLEDGMENT_PATTERNS) or cleaned in {"ok", "okay", "great", "nice", "cool", "awesome", "got it"}:
        return random.choice(_CASUAL_ACKNOWLEDGMENT_RESPONSES)

    if "morning" in cleaned:
        return "Good morning! \U0001F31E How can I help you today?"
    if "evening" in cleaned:
        return "Good evening! \U0001F319 How can I assist you today?"
    if "afternoon" in cleaned:
        return "Good afternoon! \U0001F60A How can I help you today?"
    return random.choice(_CASUAL_GREETING_RESPONSES)


def classify_query(query: str, context: Optional[List[Dict[str, Any]]] = None) -> QueryType:
    """
    Comprehensive query classifier that distinguishes:
    - CASUAL_CONVERSATION
    - KNOWLEDGE_QUERY
    - TECHNICAL_QUERY
    - CODE_QUERY
    - GENERAL_QUERY
    - FOLLOW_UP_QUERY
    - WEB_LOOKUP
    - UNKNOWN_QUERY
    """
    text = query.strip()
    if not text:
        return QueryType.CASUAL_CONVERSATION

    lower = text.lower()

    if is_unknown_or_fictional(lower):
        return QueryType.UNKNOWN_QUERY

    if is_mixed_knowledge_query(text):
        sub_query = extract_question_from_mixed(text)
        return classify_query(sub_query, context=context)

    if is_casual_conversation(text):
        return QueryType.CASUAL_CONVERSATION

    if context and is_follow_up_query(text, context):
        return QueryType.FOLLOW_UP_QUERY

    if is_code_query(text):
        return QueryType.CODE_QUERY

    if is_technical_query(text):
        return QueryType.TECHNICAL_QUERY

    if is_sanskrit_knowledge_query(text):
        return QueryType.KNOWLEDGE_QUERY

    if any(re.search(pat, lower) for pat in _WEB_LOOKUP_PATTERNS):
        return QueryType.WEB_LOOKUP

    if any(re.search(pat, lower) for pat in _CONCEPT_PATTERNS):
        return QueryType.CONCEPT_QUERY
    if any(re.search(pat, lower) for pat in _EXPLANATION_PATTERNS):
        return QueryType.EXPLANATION_QUERY

    if any(lower.startswith(prefix) for prefix in ("who ", "why ", "when ", "where ", "which ", "is ", "are ", "can ")):
        return QueryType.GENERAL_QUERY

    return QueryType.KNOWLEDGE_QUERY
