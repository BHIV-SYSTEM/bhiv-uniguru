import time
import uuid
from typing import Dict, Any
from enforcement.seal import EnforcementSealer
from verifier.source_verifier import SourceVerifier


UNVERIFIED_REFUSAL = "Verification status: UNVERIFIED. I cannot verify this information from current knowledge."


class SovereignEnforcement:
    """
    Upgraded enforcement layer.
    Mandatory global verification and cryptographic sealing.
    """

    def __init__(self):
        self.sealer = EnforcementSealer()
        self.verifier = SourceVerifier()

    def process_and_seal(self, decision_schema: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Implements: verify -> enforce -> seal -> return."""
        data = decision_schema.setdefault("data", {})
        verification_meta = data.get("verification", {}) if isinstance(data, dict) else {}
        content = str(data.get("response_content", "") or "")

        v_status = decision_schema.get("verification_status")
        if not v_status:
            truth_decl = str(verification_meta.get("truth_declaration", ""))
            if truth_decl == "VERIFIED":
                v_status = "VERIFIED"
            elif truth_decl == "VERIFIED_PARTIAL":
                v_status = "PARTIAL"
            elif decision_schema.get("decision") == "forward":
                v_status = "PARTIAL"
            else:
                v_status = "UNVERIFIED"

        decision_schema["verification_status"] = v_status

        if v_status == "VERIFIED":
            decision_schema["status_action"] = "ALLOW"
            prefix = self._resolve_declaration(verification_meta, default_source="UniGuru KB", partial=False)
            decision_schema["verification_prefix"] = prefix
            data["response_content"] = self._prefix_if_missing(content, prefix)

        elif v_status == "PARTIAL":
            decision_schema["status_action"] = "ALLOW_WITH_DISCLAIMER"
            prefix = self._resolve_declaration(
                verification_meta,
                default_source="Production UniGuru backend",
                partial=True,
            )
            decision_schema["verification_prefix"] = prefix
            decision_schema["disclaimer"] = prefix
            data["response_content"] = self._prefix_if_missing(content, prefix)

        else:
            decision_schema["status_action"] = "REFUSE"
            decision_schema["decision"] = "block"
            decision_schema["reason"] = "Refusal: source verification uncertain or unavailable."
            decision_schema["verification_prefix"] = "Verification status: UNVERIFIED"
            decision_schema["data"] = {"response_content": UNVERIFIED_REFUSAL}

        final_content = str(decision_schema.get("data", {}).get("response_content", "BLOCKED"))
        signature = self.sealer.create_signature(final_content, request_id)

        decision_schema["enforcement_signature"] = signature
        decision_schema["enforced"] = True
        decision_schema["request_id"] = request_id
        decision_schema["sealed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        return decision_schema

    def verify_bridge_seal(self, response: Dict[str, Any]) -> bool:
        """Used by bridge to verify signature before returning to caller."""
        signature = response.get("enforcement_signature")
        request_id = response.get("request_id")
        content = str(response.get("data", {}).get("response_content", "BLOCKED"))
        if not signature:
            return False
        return self.sealer.verify_signature(content, request_id, signature)

    @staticmethod
    def _prefix_if_missing(content: str, prefix: str) -> str:
        if not content:
            return prefix
        if content.startswith(prefix):
            return content
        return f"{prefix}\n\n{content}"

    @staticmethod
    def _resolve_declaration(verification_meta: Dict[str, Any], default_source: str, partial: bool) -> str:
        formatted = str(verification_meta.get("formatted_response", "") or "").strip()
        if partial and formatted.startswith("This information is partially verified from:"):
            return formatted
        if (not partial) and formatted.startswith("Based on verified source:"):
            return formatted

        source = verification_meta.get("source_name") or verification_meta.get("source_file") or default_source
        if partial:
            return f"This information is partially verified from: {source}"
        return f"Based on verified source: {source}"


class UniGuruEnforcement(SovereignEnforcement):
    """Backward-compatible adapter expected by RuleEngine."""

    def validate_and_bind(self, decision_schema: Dict[str, Any]) -> Dict[str, Any]:
        request_id = (
            decision_schema.get("data", {}).get("request_id")
            or decision_schema.get("request_id")
            or str(uuid.uuid4())
        )
        return self.process_and_seal(decision_schema, request_id)
