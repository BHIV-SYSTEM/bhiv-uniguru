"""
Guru (Chatbot) data models and in-memory storage.
For production, replace with database persistence.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Guru(BaseModel):
    """Represents a custom AI guru/chatbot created by a user."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str = Field(..., min_length=1, max_length=100)
    subject: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    is_active: bool = True


class CreateGuruRequest(BaseModel):
    """Request body for creating a custom guru."""
    name: str = Field(..., min_length=1, max_length=100)
    subject: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)


class GuruStorage:
    """In-memory storage for gurus. Replace with database in production."""
    
    def __init__(self):
        self._gurus: Dict[str, Guru] = {}
        self._user_gurus: Dict[str, List[str]] = {}  # user_id -> list of guru_ids
    
    def create_guru(self, user_id: str, name: str, subject: str, description: Optional[str] = None) -> Guru:
        """Create a new guru for a user."""
        guru = Guru(
            user_id=user_id,
            name=name,
            subject=subject,
            description=description
        )
        self._gurus[guru.id] = guru
        
        if user_id not in self._user_gurus:
            self._user_gurus[user_id] = []
        self._user_gurus[user_id].append(guru.id)
        
        return guru
    
    def get_guru(self, guru_id: str) -> Optional[Guru]:
        """Get a guru by ID."""
        return self._gurus.get(guru_id)
    
    def get_user_gurus(self, user_id: str) -> List[Guru]:
        """Get all gurus for a user."""
        guru_ids = self._user_gurus.get(user_id, [])
        return [self._gurus[gid] for gid in guru_ids if gid in self._gurus and self._gurus[gid].is_active]

    def get_all_active_gurus(self) -> List[Guru]:
        """Get all active gurus across users (demo fallback)."""
        return [guru for guru in self._gurus.values() if guru.is_active]
    
    def delete_guru(self, guru_id: str, user_id: str) -> bool:
        """Soft delete a guru (mark as inactive)."""
        guru = self._gurus.get(guru_id)
        if not guru or guru.user_id != user_id:
            return False
        
        guru.is_active = False
        guru.updated_at = datetime.utcnow().isoformat()
        return True
    
    def update_guru(self, guru_id: str, user_id: str, **updates) -> Optional[Guru]:
        """Update guru fields."""
        guru = self._gurus.get(guru_id)
        if not guru or guru.user_id != user_id:
            return None
        
        for key, value in updates.items():
            if hasattr(guru, key) and key not in ['id', 'user_id', 'created_at']:
                setattr(guru, key, value)
        
        guru.updated_at = datetime.utcnow().isoformat()
        return guru


# Global storage instance
guru_storage = GuruStorage()
