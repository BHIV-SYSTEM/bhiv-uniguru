from core.rules.base import BaseRule, RuleContext, RuleResult, RuleAction

class ForwardRule(BaseRule):
    def evaluate(self, context: RuleContext) -> RuleResult:
        # If we reached this point, the query is safe, clear, and not in the local KB.
        return RuleResult(
            action=RuleAction.FORWARD,
            reason="Query is safe and clear. Ready for legacy system processing.",
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
