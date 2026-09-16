from typing import Literal

class ResponseFormatter:
    @staticmethod
    def format_response(
        decision: Literal["answer", "fallback", "reject"],
        confidence: float,
        source: Literal["ontology", "vectorstore", "none"],
        answer: str
    ) -> dict:
        """
        Formats the final output into the required enterprise JSON schema.
        """
        return {
            "decision": decision,
            "confidence": round(confidence, 2),
            "source": source,
            "answer": answer
        }

response_formatter = ResponseFormatter()
