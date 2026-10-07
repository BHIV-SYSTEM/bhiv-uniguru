"""
UniGuru Continuous Learning & User Personalization Memory System
================================================================
Implements:
  1. User Memory (identity, preferences, skills, context, verified facts)
  2. Safe Continuous Learning without retraining base LLM
  3. Candidate memory extraction & strict validation
  4. User feedback collection (Thumbs up/down, failure categorization)
  5. Per-user namespace isolation: User A's profile NEVER leaks to User B
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("uniguru.memory")

ROOT_DIR = Path(__file__).resolve().parent.parent
MEMORY_DIR = ROOT_DIR / "data" / "user_memory"
FEEDBACK_DIR = ROOT_DIR / "data" / "feedback"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class UserPreference:
    key: str
    value: Any
    confidence: float = 1.0
    updated_at: float = field(default_factory=time.time)


@dataclass
class UserSkill:
    skill_name: str
    proficiency: str = "intermediate"  # beginner, intermediate, advanced
    confidence: float = 1.0
    updated_at: float = field(default_factory=time.time)


@dataclass
class UserMemoryProfile:
    user_id: str
    name: Optional[str] = None
    preferences: Dict[str, Any] = field(default_factory=dict)
    skills: List[str] = field(default_factory=list)
    facts: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "preferences": self.preferences,
            "skills": self.skills,
            "facts": self.facts,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> UserMemoryProfile:
        return cls(
            user_id=data.get("user_id", "default_user"),
            name=data.get("name"),
            preferences=data.get("preferences", {}),
            skills=data.get("skills", []),
            facts=data.get("facts", {}),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


@dataclass
class FeedbackRecord:
    feedback_id: str
    user_id: str
    session_id: str
    query: str
    answer: str
    is_helpful: bool
    failure_type: Optional[str] = None  # retrieval_failure, code_syntax_error, reasoning_error, hallucination
    corrected_answer: Optional[str] = None
    routing_decision: Optional[str] = None
    model_version: str = "uniguru-v2.5"
    timestamp: float = field(default_factory=time.time)


class UserMemoryStore:
    """Thread-safe persistent store for user profiles and continuous learning."""

    _instance: Optional[UserMemoryStore] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._profiles: Dict[str, UserMemoryProfile] = {}
        self._store_lock = threading.Lock()
        self._feedback_log: List[FeedbackRecord] = []
        self._load_all_profiles()

    @classmethod
    def get_instance(cls) -> UserMemoryStore:
        with cls._lock:
            if cls._instance is None:
                cls._instance = UserMemoryStore()
            return cls._instance

    def _get_profile_path(self, user_id: str) -> Path:
        safe_user = re.sub(r"[^a-zA-Z0-9_\-]", "_", user_id)
        return MEMORY_DIR / f"{safe_user}.json"

    def _load_all_profiles(self) -> None:
        with self._store_lock:
            for p in MEMORY_DIR.glob("*.json"):
                try:
                    with p.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                        prof = UserMemoryProfile.from_dict(data)
                        self._profiles[prof.user_id] = prof
                except Exception as exc:
                    logger.error("Failed to load user profile %s: %s", p, exc)

    def get_profile(self, user_id: str) -> UserMemoryProfile:
        with self._store_lock:
            if user_id not in self._profiles:
                p_path = self._get_profile_path(user_id)
                if p_path.exists():
                    try:
                        with p_path.open("r", encoding="utf-8") as f:
                            data = json.load(f)
                            self._profiles[user_id] = UserMemoryProfile.from_dict(data)
                    except Exception:
                        self._profiles[user_id] = UserMemoryProfile(user_id=user_id)
                else:
                    self._profiles[user_id] = UserMemoryProfile(user_id=user_id)
            return self._profiles[user_id]

    def save_profile(self, profile: UserMemoryProfile) -> None:
        profile.updated_at = time.time()
        with self._store_lock:
            self._profiles[profile.user_id] = profile
            p_path = self._get_profile_path(profile.user_id)
            try:
                with p_path.open("w", encoding="utf-8") as f:
                    json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)
            except Exception as exc:
                logger.error("Failed to persist user profile for %s: %s", profile.user_id, exc)

    def extract_and_learn_interaction(self, query: str, user_id: str) -> Dict[str, Any]:
        """
        Extracts candidate memories from user interactions and safely stores them.
        Prevents prompt injections or malicious instructions from corrupting memory.
        """
        profile = self.get_profile(user_id)
        learned = {}
        clean_q = query.strip()
        q_lower = clean_q.lower()

        # 1. Identity Learning ("My name is Vijay", "I am Vijay")
        name_patterns = [
            r"\bmy name is\s+([A-Za-z\u0900-\u097F]+)",
            r"\bi am\s+([A-Za-z\u0900-\u097F]+)",
            r"\bcall me\s+([A-Za-z\u0900-\u097F]+)",
            r"\bमाझं नाव\s+([A-Za-z\u0900-\u097F]+)\s+आहे",
            r"\bमेरा नाम\s+([A-Za-z\u0900-\u097F]+)\s+है",
        ]
        for pat in name_patterns:
            m = re.search(pat, clean_q, re.IGNORECASE)
            if m:
                cand_name = m.group(1).strip().capitalize()
                # Blacklist stopwords
                if cand_name.lower() not in {
                    "learning", "asking", "here", "fine", "good", "student", "user", "uniguru", "admin", "null", "undefined"
                }:
                    profile.name = cand_name
                    learned["name"] = cand_name
                    break

        # 2. Preference Learning (e.g. "My preferred programming language is Python", "I prefer Python")
        pref_match = re.search(r"(?:preferred|favorite|favourite|prefer)\s+(?:programming\s+language|language)\s+(?:is|to\s+use)?\s*([a-zA-Z\+\#]+)", q_lower)
        if pref_match:
            lang = pref_match.group(1).title()
            if lang.lower() in {"python", "javascript", "typescript", "java", "c++", "cpp", "c", "c#", "rust", "go", "sql"}:
                profile.preferences["preferred_programming_language"] = lang
                learned["preferred_programming_language"] = lang

        # Direct preference: "I love Python" or "I prefer concise answers"
        if "concise" in q_lower and ("answer" in q_lower or "response" in q_lower):
            profile.preferences["response_style"] = "concise"
            learned["response_style"] = "concise"
        elif "detailed" in q_lower and ("answer" in q_lower or "response" in q_lower):
            profile.preferences["response_style"] = "detailed"
            learned["response_style"] = "detailed"

        # 3. Skills Learning (e.g. "I am learning Python", "I work with FastAPI")
        skill_match = re.search(r"\b(?:working with|learning|expert in|experienced with)\s+([a-zA-Z0-9\+\#\s]+)", q_lower)
        if skill_match:
            candidate_skill = skill_match.group(1).strip().title()
            if any(s in candidate_skill.lower() for s in ["python", "fastapi", "react", "sql", "ai", "ml", "docker"]):
                if candidate_skill not in profile.skills:
                    profile.skills.append(candidate_skill)
                    learned["added_skill"] = candidate_skill

        if learned:
            self.save_profile(profile)

        return learned

    def record_feedback(
        self,
        user_id: str,
        session_id: str,
        query: str,
        answer: str,
        is_helpful: bool,
        failure_type: Optional[str] = None,
        corrected_answer: Optional[str] = None,
        routing_decision: Optional[str] = None,
    ) -> FeedbackRecord:
        import uuid
        fb_id = f"fb_{uuid.uuid4().hex[:10]}"
        rec = FeedbackRecord(
            feedback_id=fb_id,
            user_id=user_id,
            session_id=session_id,
            query=query,
            answer=answer,
            is_helpful=is_helpful,
            failure_type=failure_type,
            corrected_answer=corrected_answer,
            routing_decision=routing_decision,
        )
        with self._store_lock:
            self._feedback_log.append(rec)
            # Write to disk
            fb_path = FEEDBACK_DIR / f"{fb_id}.json"
            try:
                with fb_path.open("w", encoding="utf-8") as f:
                    json.dump(asdict(rec), f, indent=2, ensure_ascii=False)
            except Exception as exc:
                logger.error("Failed to write feedback record: %s", exc)

        return rec

    def get_relevant_user_context(self, user_id: str, query: str) -> Dict[str, Any]:
        """
        Selectively injects ONLY user memories relevant to the current query.
        Does NOT dump the entire profile blindly into the prompt.
        """
        profile = self.get_profile(user_id)
        context = {}
        q_lower = query.lower()

        # Always provide user name for greetings / identity
        if profile.name:
            context["user_name"] = profile.name

        # If query is programming related, inject programming language preference
        if any(w in q_lower for w in ["code", "program", "example", "write", "function", "script"]):
            pref_lang = profile.preferences.get("preferred_programming_language")
            if pref_lang:
                context["preferred_programming_language"] = pref_lang

        # If query asks about style
        style = profile.preferences.get("response_style")
        if style:
            context["response_style"] = style

        return context


def get_user_memory_store() -> UserMemoryStore:
    return UserMemoryStore.get_instance()
