from core.rules.base import BaseRule, RuleContext, RuleResult, RuleAction
from enum import Enum
from typing import Dict, List

class PowerDynamic(Enum):
    PROFESSIONAL = "professional"  # Boss, Manager, Client
    ACADEMIC = "academic"          # Teacher, Professor, Administrator
    PERSONAL = "personal"          # Parent, Friend (Emotional Pressure)
    TECHNICAL = "technical"        # Developer, Admin, Sudo (System Pressure)

class AuthorityRule(BaseRule):
    """
    Authority Pressure Model.
    Detects coercion and categorize the power dynamic.
    """
    
    DYNAMIC_TRIGGERS = {
        PowerDynamic.PROFESSIONAL: ["my boss said", "my manager", "work requirement", "on behalf of the client"],
        PowerDynamic.ACADEMIC: ["my teacher", "the professor", "academic board", "dean of studies"],
        PowerDynamic.PERSONAL: ["my parents", "my dad", "my mom", "my friend", "trust me"],
        PowerDynamic.TECHNICAL: ["sudo", "as administrator", "root access", "system override", "bypass"]
    }
    
    COERCION_TERMS = ["must", "immediately", "mandatory", "required", "no choice", "if you don't"]
    
    def evaluate(self, context: RuleContext) -> RuleResult:
        query = context.content.lower().strip()
        
        detected_dynamic = PowerDynamic.PERSONAL # Default
        found_dynamic = False
        
        for dynamic, triggers in self.DYNAMIC_TRIGGERS.items():
            if any(t in query for t in triggers):
                detected_dynamic = dynamic
                found_dynamic = True
                break
        
        # Calculate Pressure Severity Score (0.0 to 1.0)
        coercion_count = sum(1 for term in self.COERCION_TERMS if term in query)
        severity_score = min(1.0, (coercion_count * 0.3) + (0.4 if found_dynamic else 0.0))
        
        if severity_score > 0.5:
            dynamic_name = str(detected_dynamic.value)
            return RuleResult(
                action=RuleAction.BLOCK,
                reason=f"Authority pressure detected: {dynamic_name} (Severity: {float(severity_score)})",
                severity=float(severity_score),
                governance_flags={
                    "authority": True,
                    "delegation": False,
                    "emotional": False,
                    "ambiguity": False,
                    "safety": False
                },
                response_content="I recognize the external pressure or authority reference, but my safety and governance protocols take precedence. I cannot comply with requests that violate these boundaries.",
                rule_name=self.name,
                extra_metadata={
                    "power_dynamic": dynamic_name,
                    "severity_score": float(severity_score),
                    "is_coercion_attempt": True
                }
            )
            
        return RuleResult(
            action=RuleAction.ALLOW,
            reason="No significant authority pressure detected.",
            severity=float(severity_score),
            governance_flags={
                "authority": True if severity_score > 0 else False,
                "delegation": False,
                "emotional": False,
                "ambiguity": False,
                "safety": False
            },
            rule_name=self.name
        )
