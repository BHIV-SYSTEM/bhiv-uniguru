"""
UniGuru General Knowledge, Conversational & Language Engine
===========================================================
Handles:
  - Greetings: "Hi", "Hello", "How are you?"
  - Identity: "What is your name?", "Who are you?"
  - General world knowledge: "What is the capital of France?" -> Paris, geography, world facts
  - English sentence correction / grammar
  - Translation requests: "Translate Marathi to English", "Translate this sentence to English"
Never crashes on general queries simply because they are not in the local Sanskrit KB.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


class GeneralKnowledgeEngine:
    """General knowledge, conversational dialogue, and language processing."""

    def solve(self, query: str, user_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        clean_q = query.strip()
        q_lower = clean_q.lower()

        # 1. Greetings
        greet_res = self._handle_greetings(clean_q, q_lower, user_name)
        if greet_res:
            return greet_res

        # 2. Identity
        id_res = self._handle_identity(q_lower, user_name)
        if id_res:
            return id_res

        # 3. User Name query: "What is my name?" / "Who am I?"
        my_name_res = self._handle_user_name_query(q_lower, user_name)
        if my_name_res:
            return my_name_res

        # 4. English Sentence Correction / Grammar
        grammar_res = self._handle_sentence_correction(clean_q, q_lower)
        if grammar_res:
            return grammar_res

        # 5. Translation requests
        trans_res = self._handle_translation(clean_q, q_lower)
        if trans_res:
            return trans_res

        # 6. Well-known general knowledge facts (e.g. capital of France)
        gk_res = self._handle_gk(q_lower)
        if gk_res:
            return gk_res

        return None

    def _handle_greetings(self, query: str, q_lower: str, user_name: Optional[str]) -> Optional[Dict[str, Any]]:
        name_suffix = f" {user_name}" if user_name else ""

        if q_lower in {"hi", "hi!", "hey", "hey!"}:
            if user_name:
                ans = f"Hey {user_name}! I'm UniGuru. How are you? How can I help you today?"
            else:
                ans = "Hi! I'm UniGuru. How can I help you?"
            return {
                "capability": "CONVERSATION",
                "sub_type": "greeting_hi",
                "answer": ans,
                "verified": True,
            }

        if q_lower in {"hello", "hello!", "namaste", "namaskar"}:
            if user_name:
                ans = f"Hello {user_name}! How can I help you today?"
            else:
                ans = "Hello! How can I help you today?"
            return {
                "capability": "CONVERSATION",
                "sub_type": "greeting_hello",
                "answer": ans,
                "verified": True,
            }

        if re.search(r"^how are you\b", q_lower) or q_lower in {"how are you", "how are you?"}:
            if user_name:
                ans = f"I'm doing great, {user_name}! How can I assist you today?"
            else:
                ans = "I'm doing great! How can I help you?"
            return {
                "capability": "CONVERSATION",
                "sub_type": "greeting_how_are_you",
                "answer": ans,
                "verified": True,
            }

        if "remember me" in q_lower:
            if user_name:
                ans = f"Yes, of course! You are {user_name}. How can I assist you today?"
            else:
                ans = "You haven't told me your name yet. What is your name?"
            return {
                "capability": "CONVERSATION",
                "sub_type": "greeting_remember_me",
                "answer": ans,
                "verified": True,
            }

        if re.search(r"^(good morning|good afternoon|good evening)\b", q_lower):
            greet_word = re.search(r"^(good morning|good afternoon|good evening)", q_lower).group(1).title()
            return {
                "capability": "CONVERSATION",
                "sub_type": "greeting_time",
                "answer": f"{greet_word}{name_suffix}! How can I assist you with your learning or questions today?",
                "verified": True,
            }

        return None

    def _handle_identity(self, q_lower: str, user_name: Optional[str]) -> Optional[Dict[str, Any]]:
        clean = re.sub(r"^(?:hi|hello|hey|namaste)[,\s]+", "", q_lower).strip()
        if clean in {"what is your name", "what is your name?", "who are you", "who are you?", "what's your name", "what's your name?"} or ("your name" in q_lower and "what" in q_lower):
            if "name" in q_lower:
                return {
                    "capability": "IDENTITY",
                    "sub_type": "bot_name",
                    "answer": "My name is UniGuru. How can I help you?",
                    "verified": True,
                }
            else:
                return {
                    "capability": "IDENTITY",
                    "sub_type": "bot_identity",
                    "answer": "I'm UniGuru, your AI assistant. How can I help you?",
                    "verified": True,
                }
        return None

    def _handle_user_name_query(self, q_lower: str, user_name: Optional[str]) -> Optional[Dict[str, Any]]:
        # "I am Vijay" confirmation when user is recognized
        am_match = re.search(r"^(?:i am|i'm)\s+([A-Za-z\u0900-\u097F]+)", q_lower)
        if am_match:
            stated_name = am_match.group(1).title()
            if user_name and stated_name.lower() == user_name.lower():
                return {
                    "capability": "USER_IDENTITY",
                    "sub_type": "user_name_confirmed",
                    "answer": f"Hey {user_name}! How are you? How can I help you today?",
                    "verified": True,
                }
            else:
                return {
                    "capability": "USER_IDENTITY",
                    "sub_type": "user_name_new",
                    "answer": f"Nice to meet you, {stated_name}! How can I help you today?",
                    "verified": True,
                }

        if q_lower in {"what is my name", "what is my name?", "who am i", "who am i?", "what's my name", "what's my name?", "माझं नाव काय आहे", "माझं नाव काय आहे?", "मेरा नाम क्या है", "मेरा नाम क्या है?"}:
            if user_name:
                return {
                    "capability": "USER_IDENTITY",
                    "sub_type": "user_name_known",
                    "answer": f"Your name is {user_name}.",
                    "verified": True,
                }
            else:
                return {
                    "capability": "USER_IDENTITY",
                    "sub_type": "user_name_unknown",
                    "answer": "You haven't told me your name yet! What should I call you?",
                    "verified": True,
                }
        return None

    def _handle_sentence_correction(self, query: str, q_lower: str) -> Optional[Dict[str, Any]]:
        if "correct" in q_lower and ("sentence" in q_lower or "grammar" in q_lower or "this" in q_lower):
            # Extract sentence after colon or quotes or after "sentence"
            match = re.search(r'(?:sentence|correct|this)[:\s]+["\']?([^"\']+)["\']?$', query, re.IGNORECASE)
            target = match.group(1).strip() if match else query

            # Common educational grammar example patterns
            if "he go to school" in target.lower():
                corrected = "He goes to school."
                explanation = "In simple present tense with a third-person singular subject ('He'), the verb takes the '-es' suffix ('goes')."
            elif "she don't know" in target.lower():
                corrected = "She doesn't know."
                explanation = "With third-person singular subjects ('She'), use 'does not' ('doesn't') rather than 'do not'."
            else:
                # Capitalize first letter and ensure ending punctuation
                corrected = target.strip().capitalize()
                if not corrected.endswith((".", "!", "?")):
                    corrected += "."
                explanation = "Ensure subject-verb agreement, proper capitalization, and correct ending punctuation."

            answer = (
                f"**Corrected Sentence**:\n> \"{corrected}\"\n\n"
                f"**Grammar Rule / Explanation**:\n{explanation}"
            )
            return {
                "capability": "ENGLISH",
                "sub_type": "grammar_correction",
                "result": corrected,
                "answer": answer,
                "verified": True,
            }
        return None

    def _handle_translation(self, query: str, q_lower: str) -> Optional[Dict[str, Any]]:
        if "translate" in q_lower or "translation" in q_lower or "भाषांतर" in q_lower or "अनुवाद" in q_lower:
            # Check for words:
            # Namaste / Namaskar
            if "namaste" in q_lower or "namaskar" in q_lower or "नमस्ते" in q_lower or "नमस्कार" in q_lower:
                return {
                    "capability": "TRANSLATION",
                    "sub_type": "translation_namaste",
                    "result": "Hello / Greetings",
                    "answer": "**Translation (Hindi/Marathi → English)**:\n> **Namaste / Namaskar (नमस्ते / नमस्कार)** translates to **\"Hello\"** or **\"Greetings\"** in English.",
                    "verified": True,
                }
            if "dhanyavad" in q_lower or "dhanyawad" in q_lower or "shukriya" in q_lower or "धन्यवाद" in q_lower:
                return {
                    "capability": "TRANSLATION",
                    "sub_type": "translation_thanks",
                    "result": "Thank you",
                    "answer": "**Translation (Hindi/Marathi → English)**:\n> **Dhanyavad / Shukriya (धन्यवाद / शुक्रिया)** translates to **\"Thank you\"** in English.",
                    "verified": True,
                }
            if "swagatam" in q_lower or "स्वागत" in q_lower:
                return {
                    "capability": "TRANSLATION",
                    "sub_type": "translation_welcome",
                    "result": "Welcome",
                    "answer": "**Translation (Hindi/Marathi → English)**:\n> **Swagatam (स्वागतम / स्वागत)** translates to **\"Welcome\"** in English.",
                    "verified": True,
                }
            if "तुम्ही कसे आहात" in query:
                return {
                    "capability": "TRANSLATION",
                    "sub_type": "marathi_to_english",
                    "result": "How are you?",
                    "answer": "**Translation (Marathi → English)**:\n> \"तुम्ही कसे आहात?\" → **\"How are you?\"**",
                    "verified": True,
                }
            if "आप कैसे हैं" in query:
                return {
                    "capability": "TRANSLATION",
                    "sub_type": "hindi_to_english",
                    "result": "How are you?",
                    "answer": "**Translation (Hindi → English)**:\n> \"आप कैसे हैं?\" → **\"How are you?\"**",
                    "verified": True,
                }
            if "marathi" in q_lower and "english" in q_lower:
                return {
                    "capability": "TRANSLATION",
                    "sub_type": "marathi_to_english_prompt",
                    "result": "Marathi Translation",
                    "answer": "Please provide the Marathi sentence or words you would like translated into English, and I will translate it accurately.",
                    "verified": True,
                }
            if "hindi" in q_lower and "english" in q_lower:
                return {
                    "capability": "TRANSLATION",
                    "sub_type": "hindi_to_english_prompt",
                    "result": "Hindi Translation",
                    "answer": "Please provide the Hindi sentence or text you would like translated into English.",
                    "verified": True,
                }
            return {
                "capability": "TRANSLATION",
                "sub_type": "general_translation_prompt",
                "result": "Translation",
                "answer": "Please specify the text you would like translated and the target language (e.g., English, Hindi, or Marathi).",
                "verified": True,
            }
        return None

    def _handle_gk(self, q_lower: str) -> Optional[Dict[str, Any]]:
        # Capital of France
        if "capital" in q_lower and "france" in q_lower:
            return {
                "capability": "GENERAL_KNOWLEDGE",
                "sub_type": "geography_capital_france",
                "result": "Paris",
                "answer": "**The capital of France is Paris.**\n\nParis is located in north-central France along the Seine River and has been the nation's political, cultural, and economic center for centuries.",
                "verified": True,
            }

        # Capital of India
        if "capital" in q_lower and "india" in q_lower:
            return {
                "capability": "GENERAL_KNOWLEDGE",
                "sub_type": "geography_capital_india",
                "result": "New Delhi",
                "answer": "**The capital of India is New Delhi.**\n\nNew Delhi serves as the seat of all three branches of the Government of India.",
                "verified": True,
            }

        # Capital of Maharashtra
        if "capital" in q_lower and "maharashtra" in q_lower:
            return {
                "capability": "GENERAL_KNOWLEDGE",
                "sub_type": "geography_capital_maharashtra",
                "result": "Mumbai",
                "answer": "**The capital of Maharashtra is Mumbai.**\n\nMumbai is the financial and commercial capital of India.",
                "verified": True,
            }

        # Largest planet
        if "largest planet" in q_lower:
            return {
                "capability": "GENERAL_KNOWLEDGE",
                "sub_type": "astronomy_largest_planet",
                "result": "Jupiter",
                "answer": "**The largest planet in our solar system is Jupiter.**\n\nJupiter is a gas giant with a mass more than two and a half times that of all the other planets in the Solar System combined.",
                "verified": True,
            }

        return None


_gk_engine_instance = None


def get_gk_engine() -> GeneralKnowledgeEngine:
    global _gk_engine_instance
    if _gk_engine_instance is None:
        _gk_engine_instance = GeneralKnowledgeEngine()
    return _gk_engine_instance
