from __future__ import annotations

import os
import sys
import re
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from typing import Any, Dict, Optional

from core.engine import RuleEngine
from enforcement.enforcement import UniGuruEnforcement
from governance.output_guard import OutputGovernanceGuard
from ontology.registry import OntologyRegistry
from reasoning.concept_resolver import ConceptResolver
from reasoning.graph_reasoner import GraphReasoner
from reasoning.reasoning_trace import ReasoningTraceGenerator
from retrieval.web_retriever import web_retrieve
try:
    from learning_runtime.capability.curriculum_intelligence import execute_curriculum_query
except ImportError:
    execute_curriculum_query = None


UNVERIFIED_MESSAGE = "Information retrieved but not verified. I cannot verify this information from current knowledge."
UNKNOWN_MESSAGE = "I don't have verified knowledge in my knowledge base to answer that question."


class LiveUniGuruService:
    """Production-facing deterministic query orchestration."""

    def __init__(self):
        self.engine = RuleEngine()
        self.enforcement = UniGuruEnforcement()
        self.ontology_registry = OntologyRegistry()
        self.concept_resolver = ConceptResolver()
        self.graph_reasoner = GraphReasoner()
        self.output_guard = OutputGovernanceGuard()

    def _handle_small_talk(self, query: str) -> Optional[str]:
        try:
            from service.query_classifier import is_casual_conversation, generate_casual_response
        except ImportError:
            from backend.service.query_classifier import is_casual_conversation, generate_casual_response

        text = str(query or "").strip()
        if is_casual_conversation(text):
            return generate_casual_response(text)
        return None

    def _execute_curriculum_capability(
        self,
        query: str,
        student_id: Optional[str],
        context: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not context.get("curriculum_capability") or execute_curriculum_query is None:
            return None
        try:
            return execute_curriculum_query(
                query=query,
                student_id=student_id or "ANONYMOUS",
                grade=context.get("grade"),
                medium=context.get("medium"),
                subject=context.get("subject"),
            )
        except Exception:
            return None

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

        small_talk = self._handle_small_talk(user_query)
        if small_talk:
            return {
                "decision": "answer",
                "confidence": 1.0,
                "source": "small_talk",
                "answer": small_talk,
                "session_id": session_id,
                "reason": "Greeting handled directly",
                "verification_status": "VERIFIED",
                "routing": {
                    "route": "SMALL_TALK"
                }
            }

        curriculum_capability = self._execute_curriculum_capability(
            query=user_query,
            student_id=session_id,
            context=metadata,
        )

        if curriculum_capability is not None:
            capability_result = curriculum_capability.get("result") or {}
            if capability_result.get("blocked"):
                return {
                    "decision": "block",
                    "answer": None,
                    "session_id": session_id,
                    "reason": capability_result.get(
                        "block_reason",
                        "Curriculum capability blocked execution.",
                    ),
                    "verification_status": "BLOCKED",
                    "routing": {
                        "route": "ROUTE_UNIGURU",
                        "query_type": "KNOWLEDGE_QUERY",
                        "curriculum_capability": True,
                    },
                    "governance_allowed": False,
                    "governance_reason": capability_result.get("block_reason"),
                    "status_action": "BLOCK",
                    "curriculum_capability": curriculum_capability,
                }
            if capability_result.get("convergence_validated"):
                return {
                    "decision": "answer",
                    "answer": (
                        capability_result
                        .get("curriculum_intelligence", {})
                        .get("definition")
                    ),
                    "session_id": session_id,
                    "reason": "TANTRA Curriculum Intelligence capability verified.",
                    "verification_status": capability_result.get(
                        "verification_status",
                        "VERIFIED",
                    ),
                    "curriculum_capability": curriculum_capability,
                    "evidence": capability_result.get("runtime_evidence"),
                    "reasoning_trace": {
                        "sources_consulted": [
                            "tantra.curriculum_intelligence",
                            "canonical_dataset",
                            "evidence_first_retrieval",
                        ],
                        "retrieval_confidence": (
                            capability_result.get("retrieval", {})
                            .get("confidence", 0.0)
                        ),
                        "verification_status": capability_result.get(
                            "verification_status"
                        ),
                    },
                }

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
            "governance_flags": sealed.get("governance_flags", {}),
            "governance_output": sealed.get("governance_output", {}),
            "verification_status": sealed.get("verification_status"),
            "status_action": sealed.get("status_action"),
            "enforcement_signature": sealed.get("enforcement_signature"),
            "request_id": sealed.get("request_id"),
            "sealed_at": sealed.get("sealed_at"),
            "latency_ms": sealed.get("total_latency_ms"),
        }
