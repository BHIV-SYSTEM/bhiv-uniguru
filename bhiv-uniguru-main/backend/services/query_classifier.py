import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class QueryClassifier:
    def __init__(self):
        try:
            from integrations.ollama_client import OllamaClient
            self.ollama = OllamaClient()
        except Exception as e:
            logger.warning(f"Ollama client unavailable for classification: {e}")
            self.ollama = None

    def classify_query(self, query: str) -> Dict[str, Any]:
        """
        Classifies the user query to detect domain, class, and subject.
        """
        default_classification = {
            "domain": "general",
            "class_level": None,
            "subject": None,
            "topic": None,
            "intent": "general"
        }

        if not self.ollama or not self.ollama.enabled:
            return default_classification

        system_prompt = (
            "You are an expert query classifier for an AI Tutor. "
            "Your task is to analyze the user's question and extract the intended domain, class, subject, and topic. "
            "Output MUST be in strict JSON format with the following keys: "
            "'domain' (Must be one of: 'education', 'religion', or 'general'), "
            "'class_level' (e.g., '1', '5', '10' - if specified, else null), "
            "'subject' (e.g., 'English', 'mathematics', 'science' - if specified, else null), "
            "'topic' (e.g., 'Grammar', 'Photosynthesis' - if specified, else null), "
            "'intent' (e.g., 'concept_explanation', 'problem_solving', 'factual'). "
            "Reply ONLY with valid JSON and no markdown formatting or extra text."
        )

        user_prompt = f"Classify this query: {query}"
        
        try:
            response = self.ollama.generate(user_prompt, system_prompt=system_prompt)
            if response:
                import re
                json_str = re.sub(r'```json\s*', '', response).replace('```', '').strip()
                classification = json.loads(json_str)
                
                # Normalize class level
                class_level = classification.get("class_level")
                if class_level:
                    class_level = str(class_level).replace("class", "").replace("Class", "").strip()
                    classification["class_level"] = class_level
                    
                # Predict education domain if class_level is present
                if classification["class_level"] and not classification.get("domain") or classification.get("domain") not in ["education", "religion", "general"]:
                    classification["domain"] = "education" if classification["class_level"] else "general"
                    
                if not classification.get("topic"):
                    classification["topic"] = None
                    
                return classification
        except Exception as e:
            logger.error(f"Classification failed: {e}")

        return default_classification

query_classifier = QueryClassifier()
