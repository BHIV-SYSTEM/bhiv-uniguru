from core.rules.base import BaseRule, RuleContext, RuleResult, RuleAction
from retrieval.web_retriever import web_retrieve
from verifier.source_verifier import VerificationStatus

class WebRetrievalRule(BaseRule):
    """
    Phase 5: Verified Web Retrieval Rule.
    Attempts to retrieve and verify information from the web if KB fails.
    """
    def evaluate(self, context: RuleContext) -> RuleResult:
        # This rule only runs if previous rules (KB) didn't return an answer.
        # However, it should only run for queries that look like they need web info.
        
        # Call web retriever
        result = web_retrieve(context.content)
        
        status = result.get("verification_status")
        
        if status in [VerificationStatus.VERIFIED, VerificationStatus.PARTIAL] and result.get("allowed"):
            return RuleResult(
                action=RuleAction.ANSWER,
                reason=f"Verified information found via Web Retrieval ({status}).",
                severity=0.1,
                governance_flags={
                    "authority": False,
                    "delegation": False,
                    "emotional": False,
                    "ambiguity": False,
                    "safety": False
                },
                response_content=result.get("answer"),
                rule_name=self.name,
                extra_metadata={
                    "web_source": result.get("source"),
                    "verification": {
                        "truth_declaration": "VERIFIED" if status == VerificationStatus.VERIFIED else "VERIFIED_PARTIAL" if status == VerificationStatus.PARTIAL else "UNVERIFIED",
                        "verification_status": status
                    }
                }
            )
            
        return RuleResult(
            action=RuleAction.ALLOW,
            reason="Web retrieval did not find verified information. Proceeding to forward.",
            severity=0.0,
            governance_flags={},
            response_content="",
            rule_name=self.name
        )
