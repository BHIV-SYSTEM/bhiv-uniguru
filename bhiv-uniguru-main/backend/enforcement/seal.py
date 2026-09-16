import hashlib
import time

class EnforcementSealer:
    """
    Sovereign Enforcement Sealing Module.
    Handles SHA256 hash generation and signature verification for response binding.
    """

    @staticmethod
    def generate_hash(content: str, request_id: str) -> str:
        """
        Generates a SHA256 hash bound to the content and request ID.
        formula: SHA256(content + request_id)
        """
        raw_data = f"{content}{request_id}".encode("utf-8")
        return hashlib.sha256(raw_data).hexdigest()

    @staticmethod
    def create_signature(content: str, request_id: str) -> str:
        """
        Creates an enforcement signature for a response.
        """
        return EnforcementSealer.generate_hash(content, request_id)

    @staticmethod
    def verify_signature(content: str, request_id: str, signature: str) -> bool:
        """
        Verifies if the provided signature matches the content and request ID.
        Prevents tampering and bypass.
        """
        expected = EnforcementSealer.generate_hash(content, request_id)
        return expected == signature
