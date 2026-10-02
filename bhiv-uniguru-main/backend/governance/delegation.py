from core.rules.base import BaseRule, RuleContext, RuleResult, RuleAction
from enum import Enum
from typing import Dict, List

class DelegationCategory(Enum):
    ACADEMIC = "academic"   # Assignments, homework, exams
    ETHICAL = "ethical"     # Decision making, bias, personal responsibility
    LEGAL = "legal"         # Compliance, contract signing, legal action
    TECHNICAL = "technical" # Automation, code execution, system changes

class DelegationRule(BaseRule):
    """
    Explicit Delegation Detection System.
    Detects attempts to transfer responsibility to the AI.
    """
    
    CATEGORY_MAPPING = {
        DelegationCategory.ACADEMIC: [
            "write my assignment", "do my homework", "complete my exam", 
            "finish my course", "solve this for me"
        ],
        DelegationCategory.TECHNICAL: [
            "automate", "run this", "execute", "handle the system", 
            "set up", "install", "deploy"
        ],
        DelegationCategory.LEGAL: [
            "sign this", "verify compliance", "legalize", "formalize agreement"
        ],
        DelegationCategory.ETHICAL: [
            "decide for me", "what should I do", "is this right", "choose for me"
        ]
    }
    
    def evaluate(self, context: RuleContext) -> RuleResult:
        query = context.content.lower().strip()
        
        detected_category = None
        trigger_phrase = None
        
        for category, triggers in self.CATEGORY_MAPPING.items():
            for trigger in triggers:
                if trigger in query:
                    detected_category = category
                    trigger_phrase = trigger
                    break
            if detected_category:
                break
        
        if detected_category is not None:
            cat_name = str(detected_category.value)
            return RuleResult(
                action=RuleAction.BLOCK,
                reason=f"Structured delegation detected: {cat_name}",
                severity=0.7,
                governance_flags={
                    "authority": False,
                    "delegation": True,
                    "emotional": False,
                    "ambiguity": False,
                    "safety": False
                },
                response_content=f"I cannot accept delegation for {cat_name} tasks. I am an informational advisor only.",
                rule_name=self.name,
                extra_metadata={
                    "delegation_category": cat_name,
                    "trigger": str(trigger_phrase) if trigger_phrase else "",
                    "is_human_responsibility_transfer": True
                }
            )
            
        return RuleResult(
            action=RuleAction.ALLOW,
            reason="No delegation attempt detected.",
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
