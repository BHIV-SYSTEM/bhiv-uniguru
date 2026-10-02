from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
import time

class RuleAction(Enum):
    ALLOW = "allow"      # Pass to next rule
    BLOCK = "block"      # Terminate (Rejection)
    ANSWER = "answer"    # Terminate (Deterministic Response)
    FORWARD = "forward"  # Terminate (Handover to Legacy)

@dataclass(frozen=True)
class RuleContext:
    request_id: str
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RuleTrace:
    rule_name: str
    action: RuleAction
    reason: str
    latency_ms: float

@dataclass
class RuleResult:
    action: RuleAction
    reason: str
    severity: float = 0.0
    governance_flags: Dict[str, Any] = field(default_factory=lambda: {
        "authority": False,
        "delegation": False,
        "emotional": False,
        "ambiguity": False,
        "safety": False
    })
    response_content: Optional[str] = None
    rule_name: Optional[str] = None
    trace: List[RuleTrace] = field(default_factory=list)
    extra_metadata: Dict[str, Any] = field(default_factory=dict)

class BaseRule(ABC):
    @property
    def name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def evaluate(self, context: RuleContext) -> RuleResult:
        """
        Evaluate the rule against the context.
        Must be deterministic.
        """
        pass
