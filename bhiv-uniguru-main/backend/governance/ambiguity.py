from core.rules.base import BaseRule, RuleContext, RuleResult, RuleAction
from enum import Enum
from typing import List, Dict

class AmbiguityClass(Enum):
    SEMANTIC = "semantic"       # Vague action/topic terms
    CONTEXTUAL = "contextual"   # Vague pronouns without referent
    INCOMPLETE = "incomplete"   # Single word or fragment

class AmbiguityRule(BaseRule):
    """
    Hardened Ambiguity Detection Framework.
    Identifies and categorizes vague queries deterministically.
    """
    
    VAGUE_PRONOUNS = ["this", "that", "it", "something", "anything", "everything"]
    VAGUE_ACTIONS = ["do", "handle", "process", "fix", "help"]
    
    def evaluate(self, context: RuleContext) -> RuleResult:
        query = context.content.strip().lower()
        tokens = query.split()
        
        flags = []
        ambiguity_class = None
        
        # 1. Incomplete Query Detection
        if len(tokens) <= 1:
            flags.append("TOKEN_COUNT_MINIMAL")
            ambiguity_class = AmbiguityClass.INCOMPLETE
            
        # 2. Contextual Ambiguity (Vague Pronouns)
        elif all(t in self.VAGUE_PRONOUNS or t in ["?", "."] for t in tokens):
            flags.append("VAGUE_PRONOUN_ONLY")
            ambiguity_class = AmbiguityClass.CONTEXTUAL
            
        # 3. Semantic Ambiguity (Only vague action + vague pronoun)
        elif len(tokens) <= 3 and any(t in self.VAGUE_ACTIONS for t in tokens) and any(t in self.VAGUE_PRONOUNS for t in tokens):
            flags.append("VAGUE_ACTION_PRONOUN_COMBO")
            ambiguity_class = AmbiguityClass.SEMANTIC

        if ambiguity_class:
            return RuleResult(
                action=RuleAction.ANSWER,
                reason=f"Ambiguity detected: {ambiguity_class.value}",
                severity=0.4,
                governance_flags={
                    "authority": False,
                    "delegation": False,
                    "emotional": False,
                    "ambiguity": True,
                    "safety": False
                },
                response_content="I'm sorry, I'm not sure I understand your request. Could you please provide more context? (e.g., specify exactly 'this' or 'that')",
                rule_name=self.name,
                extra_metadata={
                    "ambiguity_class": ambiguity_class.value,
                    "flags": flags,
                    "deterministic_score": 1.0
                }
            )
        
        return RuleResult(
            action=RuleAction.ALLOW,
            reason="Query clarity verified.",
            severity=0.0,
            governance_flags={
                "authority": False,
                "delegation": False,
                "emotional": False,
                "ambiguity": False,
                "safety": False
            },
            rule_name=self.name
        )
