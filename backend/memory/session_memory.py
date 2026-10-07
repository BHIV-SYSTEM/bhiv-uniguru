"""
UniGuru Session & Multi-Turn Conversation Memory
=================================================
Thread-safe, bounded, per-session conversational memory.
Features:
  - User name extraction & safe recall ("My name is Vijay" -> "Your name is Vijay")
  - Topic / Entity tracking for follow-ups ("Explain Karma Yoga" -> "Explain it simply")
  - Last query and last answer caching
  - Bounded history (default max 10 turns)
  - Strict isolation: User A's context never leaks to User B
"""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ConversationTurn:
    query: str
    answer: str
    intent: str
    timestamp: float = field(default_factory=time.time)
    entities: List[str] = field(default_factory=list)


@dataclass
class SessionState:
    session_id: str
    user_id: str
    user_name: Optional[str] = None
    last_topic: Optional[str] = None
    last_query: Optional[str] = None
    last_answer: Optional[str] = None
    turns: List[ConversationTurn] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)

    def add_turn(self, query: str, answer: str, intent: str, entities: Optional[List[str]] = None) -> None:
        self.last_query = query
        self.last_answer = answer
        self.last_activity = time.time()
        if entities:
            self.last_topic = entities[0]
        
        turn = ConversationTurn(
            query=query,
            answer=answer,
            intent=intent,
            entities=entities or [],
        )
        self.turns.append(turn)
        # Keep bounded history (last 10 turns)
        if len(self.turns) > 10:
            self.turns = self.turns[-10:]

    def get_history_context(self, max_turns: int = 4) -> str:
        """Format recent dialogue for context expansion / LLM prompt."""
        recent = self.turns[-max_turns:]
        lines = []
        for t in recent:
            lines.append(f"User: {t.query}")
            lines.append(f"UniGuru: {t.answer[:200]}...")
        return "\n".join(lines)


class SessionMemoryManager:
    """Thread-safe manager for all active session memories."""

    _instance: Optional[SessionMemoryManager] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionState] = {}
        self._store_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> SessionMemoryManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = SessionMemoryManager()
            return cls._instance

    def _session_key(self, session_id: Optional[str], user_id: Optional[str]) -> str:
        s = (session_id or "").strip()
        u = (user_id or "").strip()
        if not s and not u:
            return "default_session"
        return f"{u}::{s}" if u and s else (s or u)

    def get_session(self, session_id: Optional[str], user_id: Optional[str] = None) -> SessionState:
        key = self._session_key(session_id, user_id)
        with self._store_lock:
            if key not in self._sessions:
                self._sessions[key] = SessionState(
                    session_id=session_id or "default_session",
                    user_id=user_id or "default_user",
                )
            return self._sessions[key]

    def extract_and_set_user_name(self, text: str, session: SessionState) -> Optional[str]:
        """Detect expressions like 'My name is Vijay', 'I am Vijay', 'Call me Vijay'."""
        patterns = [
            r"\bmy name is\s+([A-Za-z\u0900-\u097F]+)",
            r"\bi am\s+([A-Za-z\u0900-\u097F]+)",
            r"\bcall me\s+([A-Za-z\u0900-\u097F]+)",
            r"\bmine name is\s+([A-Za-z\u0900-\u097F]+)",
            r"\bमाझं नाव\s+([A-Za-z\u0900-\u097F]+)\s+आहे",
            r"\bमेरा नाम\s+([A-Za-z\u0900-\u097F]+)\s+है",
        ]
        for p in patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip().capitalize()
                # Exclude false positives like 'learning', 'asking', 'student'
                if name.lower() not in {"learning", "asking", "here", "fine", "good", "student", "user", "uniguru"}:
                    session.user_name = name
                    return name
        return None

    def resolve_followup_reference(self, query: str, session: SessionState) -> str:
        """Resolve pronouns ('it', 'this', 'that', 'explain more', 'give an example') to last topic."""
        q_lower = query.strip().lower()
        
        # Check if query contains reference words
        reference_patterns = [
            r"\b(explain|simplify|summarize|clarify|elaborate|details on)\s+(it|this|that|the same)\b",
            r"\b(give|show|tell)\s+(me\s+)?an?\s+example\b",
            r"^(explain|simplify)\s+it\b",
            r"^give\s+an?\s+example\b",
            r"^tell\s+me\s+more\b",
            r"^what\s+about\s+(it|this|that)\b",
            r"^आणखी\s+सांगा\b",
            r"^उदाहरण\s+द्या\b",
            r"^और\s+बताइए\b",
            r"^उदाहरण\s+दीजिए\b",
        ]
        is_followup = any(re.search(p, q_lower) for p in reference_patterns)
        
        if is_followup and session.last_topic:
            # Expand query with context
            if "example" in q_lower:
                return f"Give an example of {session.last_topic}"
            if "simplify" in q_lower or "simply" in q_lower:
                return f"Explain {session.last_topic} simply"
            if "explain" in q_lower:
                return f"Explain {session.last_topic}"
            return f"{query} regarding {session.last_topic}"
            
        return query


def get_session_manager() -> SessionMemoryManager:
    return SessionMemoryManager.get_instance()
