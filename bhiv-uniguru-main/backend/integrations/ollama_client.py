
import logging
import os
import requests
import json
from typing import Optional, Dict, Any

logger = logging.getLogger("recipe ai.ollama")

class OllamaClient:
    """
    Client for interacting with local Ollama service.
    """
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", "llama2")
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "30"))
        self.enabled = os.getenv("UNIGURU_OLLAMA_ENABLED", "false").lower() in ("true", "1", "yes")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """
        Generate a response from Ollama.
        """
        if not self.enabled:
            logger.warning("Ollama is disabled via configuration.")
            return None

        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        if system_prompt:
            payload["system"] = system_prompt

        try:
            logger.info(f"Calling Ollama ({self.model}) at {url}")
            response = requests.post(url, json=payload, timeout=(1.5, self.timeout))
            response.raise_for_status()
            
            data = response.json()
            return data.get("response", "").strip()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama connection error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling Ollama: {e}")
            return None

    def chat(self, messages: list) -> Optional[str]:
        """
        Chat with Ollama using message history.
        """
        if not self.enabled:
            return None

        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }

        try:
            response = requests.post(url, json=payload, timeout=(1.5, self.timeout))
            response.raise_for_status()
            
            data = response.json()
            return data.get("message", {}).get("content", "").strip()
            
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            return None
