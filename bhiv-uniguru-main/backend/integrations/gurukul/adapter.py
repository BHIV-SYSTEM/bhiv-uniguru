from typing import Optional, Dict, Any

from pydantic import BaseModel

from ontology.registry import OntologyRegistry


class GurukulQueryRequest(BaseModel):
    student_query: str
    student_id: Optional[str] = None
    class_id: Optional[str] = None
    session_id: Optional[str] = None


class GurukulIntegrationAdapter:
    """Adapter that binds Gurukul student queries to UniGuru RuleEngine."""

    def __init__(self, engine):
        self.engine = engine
        self.ontology_registry = OntologyRegistry()

    def process_student_query(self, payload: GurukulQueryRequest) -> Dict[str, Any]:
        metadata = {
            "source_system": "gurukul",
            "student_id": payload.student_id,
            "class_id": payload.class_id,
            "session_id": payload.session_id,
        }
        decision = self.engine.evaluate(payload.student_query, metadata)
        ontology_reference = decision.get("ontology_reference") or self.ontology_registry.default_reference()
        ontology_contract = self.ontology_registry.get_registry_contract(ontology_reference)

        return {
            "integration": "gurukul",
            "student_id": payload.student_id,
            "class_id": payload.class_id,
            "session_id": payload.session_id,
            "verification_status": decision.get("verification_status"),
            "status_action": decision.get("status_action"),
            "ontology_reference": ontology_reference,
            "ontology_registry_contract": ontology_contract,
            "response": decision,
        }
