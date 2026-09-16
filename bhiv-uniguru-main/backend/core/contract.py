from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

class SafetyStatus(Enum):
    ALLOWED = "ALLOWED"
    DENIED = "DENIED"
    FLAGGED = "FLAGGED"

@dataclass
class ReasoningRequest:
    query: str
    context: Dict = field(default_factory=dict)
    history: List[str] = field(default_factory=list)

@dataclass
class ReasoningResponse:
    reasoning: str
    conclusion: str
    metadata: Dict = field(default_factory=dict)
    status: SafetyStatus = SafetyStatus.ALLOWED
    error_message: Optional[str] = None
