from core.rules.base import BaseRule, RuleContext, RuleResult, RuleAction

class SafetyRule(BaseRule):
    def __init__(self):
        self.prohibited_terms = [
            "cheat",
            "exam answers",
            "hack",
            "bypass security",
            "exploit",
            "vulnerability",
            "malware",
            "illegal",
            "bypass the system",
            "<script>"
        ]

    def evaluate(self, context: RuleContext) -> RuleResult:
        query = context.content.lower().strip()
        
        for term in self.prohibited_terms:
            if term in query:
                return RuleResult(
                    action=RuleAction.BLOCK,
                    reason=f"Prohibited content detected: '{term}'",
                    severity=1.0,
                    governance_flags={
                        "authority": False,
                        "delegation": False,
                        "emotional": False,
                        "ambiguity": False,
                        "safety": True
                    },
                    response_content="I cannot assist with academic dishonesty, illegal activities, or system bypassing.",
                    rule_name=self.name
                )
        
        return RuleResult(
            action=RuleAction.ALLOW,
            reason="No unsafe content detected.",
            rule_name=self.name
        )
