import re

class ValidationService:
    @staticmethod
    def validate_query(query: str) -> dict:
        """
        Validates the user query for security and quality.
        """
        query = query.strip()
        
        if not query:
            return {"is_valid": False, "error": "Query cannot be empty."}
        
        if len(query) < 3:
            return {"is_valid": False, "error": "Query is too short."}
            
        if len(query) > 2000:
            return {"is_valid": False, "error": "Query exceeds maximum character limit."}

        # Basic malicious pattern detection (SQLi, Scripting)
        malicious_patterns = [
            r"DROP TABLE", r"DELETE FROM", r"<script>", r"OR 1=1",
            r"truncate", r"grant\s+all", r"UNION SELECT"
        ]
        
        for pattern in malicious_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return {"is_valid": False, "error": "Security violation: Potential malicious query detected."}

        return {"is_valid": True, "error": None}

validation_service = ValidationService()
