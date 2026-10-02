from __future__ import annotations

from typing import Any, Dict, Optional

from core.engine import RuleEngine
from enforcement.enforcement import UniGuruEnforcement
from governance.output_guard import OutputGovernanceGuard
from ontology.registry import OntologyRegistry
from reasoning.concept_resolver import ConceptResolver
from reasoning.graph_reasoner import GraphReasoner
from reasoning.reasoning_trace import ReasoningTraceGenerator
from retrieval.web_retriever import web_retrieve


UNVERIFIED_MESSAGE = "Information retrieved but not verified. I cannot verify this information from current knowledge."
UNKNOWN_MESSAGE = "I do not have verified knowledge to answer this question."


class LiveUniGuruService:
    """Production-facing deterministic query orchestration."""

    def __init__(self):
        self.engine = RuleEngine()
        self.enforcement = UniGuruEnforcement()
        self.ontology_registry = OntologyRegistry()
        self.concept_resolver = ConceptResolver()
        self.graph_reasoner = GraphReasoner()
        self.output_guard = OutputGovernanceGuard()

    def ask(
        self,
        user_query: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        allow_web_retrieval: bool = False,
    ) -> Dict[str, Any]:
        metadata = dict(context or {})
        metadata["session_id"] = session_id
        metadata["allow_web_retrieval"] = allow_web_retrieval

        decision = self.engine.evaluate(
            content=user_query,
            metadata=metadata,
            apply_enforcement=False,
        )

        if decision.get("decision") == "forward":
            if allow_web_retrieval:
                decision = self._resolve_with_web(decision=decision, query=user_query)
            else:
                decision = self._resolve_unknown(decision)

        self._attach_reasoning_trace(decision)
        self._apply_output_governance(decision)
        sealed = self.enforcement.validate_and_bind(decision)
        return self._build_contract_response(sealed, session_id=session_id)

    def _resolve_unknown(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        data = decision.setdefault("data", {})
        decision["decision"] = "block"
        decision["reason"] = "No verified KB response and web retrieval is disabled."
        data["response_content"] = UNKNOWN_MESSAGE
        data["verification"] = {
            "truth_declaration": "UNVERIFIED",
            "verification_status": "UNVERIFIED",
            "formatted_response": UNVERIFIED_MESSAGE,
            "source_name": "None",
        }
        return decision

    def _resolve_with_web(self, decision: Dict[str, Any], query: str) -> Dict[str, Any]:
        web_result = web_retrieve(query)
        data = decision.setdefault("data", {})

        status = str(web_result.get("verification_status") or "UNVERIFIED").upper()
        allowed = bool(web_result.get("allowed"))
        if allowed and status in {"VERIFIED", "PARTIAL"}:
            concept_resolution = self.concept_resolver.resolve(query=query, retrieval_trace=None)
            reasoning_path = self.graph_reasoner.reasoning_path_from_domain_root(
                concept_id=concept_resolution["concept_id"],
                domain=concept_resolution["domain"],
            )
            data["concept_resolution"] = concept_resolution
            data["reasoning_path"] = reasoning_path
            data["reasoning_trace"] = ReasoningTraceGenerator.from_reasoning_path(
                reasoning_path=reasoning_path,
                snapshot_version=concept_resolution["snapshot_version"],
                snapshot_hash=concept_resolution["snapshot_hash"],
            )
            data["retrieval_trace"] = {
                "engine": "WebRetriever_v1",
                "match_found": True,
                "confidence": 1.0 if status == "VERIFIED" else 0.6,
                "kb_file": None,
                "sources_consulted": [
                    concept_resolution["domain"],
                    "web",
                    "ontology_registry",
                    "ontology_graph",
                ],
                "web_source": web_result.get("source"),
            }
            data["web_source"] = {
                "url": web_result.get("source"),
                "title": web_result.get("source_title"),
            }
            truth_decl = "VERIFIED" if status == "VERIFIED" else "VERIFIED_PARTIAL"
            data["verification"] = {
                "truth_declaration": truth_decl,
                "verification_status": status,
                "formatted_response": web_result.get("truth_declaration"),
                "source_name": web_result.get("source_title") or web_result.get("source"),
            }
            data["response_content"] = str(web_result.get("answer") or "")
            decision["decision"] = "answer"
            decision["reason"] = f"Web retrieval succeeded with status {status}."
            decision["ontology_reference"] = self.ontology_registry.build_reference(
                decision="answer",
                trace=data.get("retrieval_trace"),
                resolved_concept=concept_resolution,
                reasoning_path=reasoning_path,
            )
            return decision

        decision["decision"] = "block"
        decision["reason"] = "Information retrieved but not verified."
        data["response_content"] = UNVERIFIED_MESSAGE
        data["web_source"] = {
            "url": web_result.get("source"),
            "title": web_result.get("source_title"),
        }
        data["verification"] = {
            "truth_declaration": "UNVERIFIED",
            "verification_status": "UNVERIFIED",
            "formatted_response": UNVERIFIED_MESSAGE,
            "source_name": web_result.get("source_title") or "Unverified web source",
        }
        return decision

    def _apply_output_governance(self, decision: Dict[str, Any]) -> None:
        data = decision.setdefault("data", {})
        response_content = str(data.get("response_content") or "")
        result = self.output_guard.evaluate(response_content)
        decision["governance_output"] = {
            "allowed": result.allowed,
            "reason": result.reason,
            "flags": result.flags,
        }
        decision.setdefault("governance_flags", {}).update(result.flags)

        if result.allowed:
            return

        decision["decision"] = "block"
        decision["reason"] = result.reason
        data["response_content"] = UNVERIFIED_MESSAGE
        data["verification"] = {
            "truth_declaration": "UNVERIFIED",
            "verification_status": "UNVERIFIED",
            "formatted_response": UNVERIFIED_MESSAGE,
            "source_name": "Output Governance",
        }

    def _attach_reasoning_trace(self, decision: Dict[str, Any]) -> None:
        data = decision.get("data", {})
        retrieval_trace = data.get("retrieval_trace") or {}
        verification = data.get("verification") or {}
        ontology_reference = decision.get("ontology_reference") or self.ontology_registry.default_reference()

        sources_consulted = list(retrieval_trace.get("sources_consulted") or [])
        sources_consulted.extend(["ontology_registry", "ontology_graph"])
        web_source = data.get("web_source") or {}
        if web_source.get("url"):
            sources_consulted.append(web_source["url"])
        sources_consulted = list(dict.fromkeys(sources_consulted))

        decision["reasoning_trace"] = {
            "sources_consulted": sources_consulted,
            "retrieval_confidence": float(retrieval_trace.get("confidence", 0.0) or 0.0),
            "ontology_domain": ontology_reference.get("domain", "core"),
            "verification_status": verification.get("verification_status")
            or self._derive_verification_status(decision),
            "verification_details": verification.get("truth_declaration", "UNVERIFIED"),
        }

    @staticmethod
    def _derive_verification_status(decision: Dict[str, Any]) -> str:
        verification = (decision.get("data") or {}).get("verification") or {}
        truth_decl = str(verification.get("truth_declaration") or "")
        if truth_decl == "VERIFIED":
            return "VERIFIED"
        if truth_decl == "VERIFIED_PARTIAL":
            return "PARTIAL"
        return "UNVERIFIED"

    def _build_contract_response(self, sealed: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        ontology_reference = sealed.get("ontology_reference") or self.ontology_registry.default_reference()
        data = sealed.get("data", {})
        reasoning_trace = sealed.get("reasoning_trace") or {}
        return {
            "decision": sealed.get("decision"),
            "answer": data.get("response_content"),
            "session_id": session_id,
            "reason": sealed.get("reason"),
            "ontology_reference": {
                "concept_id": ontology_reference.get("concept_id"),
                "domain": ontology_reference.get("domain"),
                "snapshot_version": ontology_reference.get("snapshot_version"),
                "snapshot_hash": ontology_reference.get("snapshot_hash"),
                "truth_level": ontology_reference.get("truth_level"),
            },
            "reasoning_trace": reasoning_trace,
            "retrieval_trace": data.get("retrieval_trace"),
            "verification": data.get("verification"),
            "governance_flags": sealed.get("governance_flags", {}),
            "governance_output": sealed.get("governance_output", {}),
            "verification_status": sealed.get("verification_status"),
            "status_action": sealed.get("status_action"),
            "enforcement_signature": sealed.get("enforcement_signature"),
            "request_id": sealed.get("request_id"),
            "sealed_at": sealed.get("sealed_at"),
            "latency_ms": sealed.get("total_latency_ms"),
        }
