# UniGuru as Deterministic Middleware

## 1. What is Middleware?
In backend engineering, **Middleware** is software that sits between the raw network request and the final application logic. It intercepts the incoming data, performs a transformation or validation, and either passes the request onward or terminates it (blocks).

## 2. Where UniGuru Sits
UniGuru is **"Reasoning Middleware."** It does not store user data; it validates the *intent* and *safety* of a request before it reaches a deeper system (like an LLM or a Database).

### Lifecycle Analogies
*   **NodeJS/Express**: Like a `router.use((req, res, next) => { ... })` function that checks for a valid header before allowing access to a route.
*   **FastAPI**: Like a `Depends()` dependency or a `BaseHTTPMiddleware` that wraps every endpoint.

## 3. The UniGuru Bridge
UniGuru acts as a bridge between a **Stochastic Client** (User) and a **Production Core**. It ensures that no matter how unstructured or dangerous the user's message is, the output delivered to the production environment is:
1.  **Audited** (Governance)
2.  **Classified** (Reasoning)
3.  **Grounded** (Retrieval)

## 4. Deterministic Requirement
Middleware in high-security systems **must** be deterministic. If a bridge operates on "probabilities" (like an LLM), it introduces non-deterministic security holes. By making UniGuru deterministic, we guarantee that the "Security Gate" never sleeps and never guesses.

## Middleware Example (from middleware_example.py)

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

app = FastAPI(title="UniGuru Middleware Example")

# --- Dummy Implementation components ---

class Governance:
    @staticmethod
    def is_safe(text: str) -> bool:
        # Block dangerous patterns
        forbidden = ["hack", "sudo", "bypass"]
        return not any(word in text.lower() for word in forbidden)

class Reasoning:
    @staticmethod
    def classify(text: str) -> str:
        # Simple deterministic classification
        if len(text.split()) < 3:
            return "AMBIGUOUS"
        return "QUALIFIED"

class Retriever:
    KB = {
        "qubit": "A qubit is the basic unit of quantum information.",
        "quantum": "Quantum mechanics is a fundamental theory in physics."
    }
    
    @staticmethod
    def match(text: str) -> str:
        text = text.lower()
        for key, val in Retriever.KB.items():
            if key in text:
                return f"[KB Match: {key}] {val}"
        return "General system knowledge used."

class Enforcement:
    @staticmethod
    def audit(response: str) -> bool:
        # Final safety check: no leaks of internal strings
        leak_patterns = ["password:", "admin_key:"]
        return not any(p in response.lower() for p in leak_patterns)

# --- API Contracts ---

class ChatRequest(BaseModel):
    message: str

# --- Middleware-like flow in endpoint ---

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    query = request.message

    # 1. Governance Layer (Pre)
    if not Governance.is_safe(query):
        return {"status": "BLOCKED", "reason": "Governance Violation", "response": "Safety policy violation."}

    # 2. Reasoning Layer
    intent = Reasoning.classify(query)
    if intent == "AMBIGUOUS":
        return {"status": "CLARIFY", "response": "Please provide more context."}

    # 3. Retrieval Layer
    knowledge = Retriever.match(query)

    # 4. Final Construction
    final_output = f"UniGuru Processed Response: {knowledge}"

    # 5. Enforcement Layer (Post)
    if not Enforcement.audit(final_output):
        raise HTTPException(status_code=500, detail="Internal Safety Fault")

    return {
        "status": "SUCCESS",
        "data": {
            "query": query,
            "response": final_output
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
```
