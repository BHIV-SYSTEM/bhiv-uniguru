import time
import uuid
from typing import Dict, Any, Optional

from core.rules.base import RuleContext, RuleResult, RuleAction
from core.rules import (
    SafetyRule,
    AuthorityRule,
    DelegationRule,
    EmotionalRule,
    AmbiguityRule,
    RetrievalRule,
    ForwardRule,
)
from enforcement.enforcement import UniGuruEnforcement
from ontology.registry import OntologyRegistry
from reasoning.concept_resolver import ConceptResolver
from reasoning.graph_reasoner import GraphReasoner
from reasoning.reasoning_trace import ReasoningTraceGenerator


class RuleEngine:
    def __init__(self):
        # Deterministic sovereign order: no external web retrieval in core path.
        self.rules = [
            SafetyRule(),
            AuthorityRule(),
            DelegationRule(),
            EmotionalRule(),
            AmbiguityRule(),
            RetrievalRule(),
            ForwardRule(),
        ]
        self.enforcement = UniGuruEnforcement()
        self.ontology_registry = OntologyRegistry()
        self.concept_resolver = ConceptResolver()
        self.graph_reasoner = GraphReasoner()

    def evaluate(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        apply_enforcement: bool = True,
    ) -> Dict[str, Any]:
        """Production-grade deterministic evaluation pipeline."""
        request_id = str(uuid.uuid4())
        context = RuleContext(
            request_id=request_id,
            content=content,
            metadata=metadata or {},
        )

        aggregated_flags = {
            "authority": False,
            "delegation": False,
            "emotional": False,
            "ambiguity": False,
            "safety": False,
        }
        max_severity = 0.0
        final_result: Optional[RuleResult] = None
        trace = []

        start_time_total = time.perf_counter()

        try:
            for rule in self.rules:
                if isinstance(rule, ForwardRule) and aggregated_flags.get("safety"):
                    break

                start_time_rule = time.perf_counter()
                result = rule.evaluate(context)
                end_time_rule = time.perf_counter()

                for flag, value in result.governance_flags.items():
                    if value:
                        aggregated_flags[flag] = True

                max_severity = max(max_severity, result.severity)

                latency_ms = (end_time_rule - start_time_rule) * 1000
                trace.append(
                    {
                        "rule": rule.name,
                        "action": result.action.value,
                        "reason": result.reason,
                        "latency_ms": round(float(latency_ms), 3),
                    }
                )

                if result.action == RuleAction.ALLOW:
                    continue

                if result.action in [RuleAction.ANSWER, RuleAction.FORWARD, RuleAction.BLOCK]:
                    final_result = result
                    break

            if final_result is None:
                final_result = RuleResult(
                    action=RuleAction.FORWARD,
                    reason="No KB match found, forwarding to production.",
                    severity=0.3,
                    governance_flags=aggregated_flags,
                    response_content="",
                )

            output = {
                "decision": final_result.action.value,
                "severity": float(max_severity),
                "governance_flags": aggregated_flags,
                "reason": final_result.reason,
                "pipeline": [
                    "Input",
                    "Governance",
                    "Retrieval",
                    "Source Verification",
                    "Concept Resolution",
                    "Ontology Reasoning",
                    "Enforcement",
                    "Response",
                ],
                "data": {
                    "response_content": final_result.response_content,
                    "rule_triggered": final_result.rule_name or final_result.__class__.__name__,
                    "request_id": request_id,
                    "trace": trace,
                },
                "enforced": False,
            }

            if final_result.extra_metadata:
                output["data"].update(final_result.extra_metadata)

            retrieval_trace = output["data"].get("retrieval_trace")
            reasoning_path = []
            concept_resolution = None
            reasoning_trace = None
            retrieval_succeeded = bool(
                final_result.action == RuleAction.ANSWER
                and isinstance(retrieval_trace, dict)
                and retrieval_trace.get("match_found")
            )
            if retrieval_succeeded:
                concept_resolution = self.concept_resolver.resolve(
                    query=content,
                    retrieval_trace=retrieval_trace,
                )
                reasoning_path = self.graph_reasoner.reasoning_path_from_domain_root(
                    concept_id=concept_resolution["concept_id"],
                    domain=concept_resolution["domain"],
                )
                reasoning_trace = ReasoningTraceGenerator.from_reasoning_path(
                    reasoning_path=reasoning_path,
                    snapshot_version=concept_resolution["snapshot_version"],
                    snapshot_hash=concept_resolution["snapshot_hash"],
                )
                output["data"]["concept_resolution"] = concept_resolution
                output["data"]["reasoning_path"] = reasoning_path
                output["data"]["reasoning_trace"] = reasoning_trace
                output["data"]["ontology_relationships"] = {
                    "traversed_nodes": len(reasoning_path),
                    "path": [
                        {
                            "concept_id": node.get("concept_id"),
                            "parent_child_chain_node": node.get("canonical_name"),
                        }
                        for node in reasoning_path
                    ],
                }
                if isinstance(retrieval_trace, dict):
                    consulted = list(retrieval_trace.get("sources_consulted") or [])
                    consulted.extend(["ontology_registry", "ontology_graph"])
                    retrieval_trace["sources_consulted"] = sorted(set(consulted))

            output["ontology_reference"] = self.ontology_registry.build_reference(
                decision=output["decision"],
                trace=retrieval_trace,
                resolved_concept=concept_resolution,
                reasoning_path=reasoning_path,
            )

            total_latency_ms = (time.perf_counter() - start_time_total) * 1000
            output["total_latency_ms"] = round(float(total_latency_ms), 2)
            if not apply_enforcement:
                return output

            final_output = self.enforcement.validate_and_bind(output)
            final_output["total_latency_ms"] = output["total_latency_ms"]
            return final_output

        except Exception as e:
            return {
                "decision": "block",
                "severity": 1.0,
                "governance_flags": aggregated_flags,
                "reason": f"Engine Crash: {str(e)}",
                "data": {
                    "response_content": "Verification status: UNVERIFIED. I cannot verify this information from current knowledge."
                },
                "enforced": False,
                "verification_status": "UNVERIFIED",
            }


if __name__ == "__main__":
    engine = RuleEngine()
    print(engine.evaluate("What is a qubit?"))
    print(engine.evaluate("hack the system"))
