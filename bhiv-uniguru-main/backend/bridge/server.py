import os
import time
import uuid
from typing import Any, Dict, Optional

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from core.engine import RuleEngine
from enforcement.enforcement import SovereignEnforcement
from integrations.gurukul.adapter import GurukulIntegrationAdapter, GurukulQueryRequest

app = FastAPI(title="UniGuru Sovereign Bridge")

PYTHON_ENGINE_URL = os.getenv("UNIGURU_ENGINE_URL", "http://127.0.0.1:8000/ask")
UNIGURU_API_TOKEN = os.getenv("UNIGURU_API_TOKEN", "").strip()

engine = RuleEngine()
enforcer = SovereignEnforcement()
gurukul_adapter = GurukulIntegrationAdapter(engine=engine)


class ChatRequest(BaseModel):
    message: Optional[str] = None
    question: Optional[str] = None
    query: Optional[str] = None
    session_id: Optional[str] = None
    caller: str = "uniguru-frontend"
    allow_web: bool = False
    context: Optional[Dict[str, Any]] = None
    source: str = "bridge_v3"


def _extract_answer(payload: Dict[str, Any]) -> str:
    return str(
        payload.get("answer")
        or (payload.get("aiResponse") or {}).get("content")
        or (payload.get("data") or {}).get("response")
        or ""
    )


def _build_engine_headers(caller: str) -> Dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "X-Caller-Name": caller,
    }
    if UNIGURU_API_TOKEN:
        headers["Authorization"] = f"Bearer {UNIGURU_API_TOKEN}"
    return headers


@app.post("/chat")
async def chat_bridge(request: ChatRequest):
    trace_id = str(uuid.uuid4())
    start_time = time.time()
    user_msg = request.message or request.question or request.query

    if not user_msg:
        raise HTTPException(status_code=400, detail="No valid query provided.")

    decision = engine.evaluate(
        user_msg,
        {
            "session_id": request.session_id,
            "trace_id": trace_id,
            "caller": request.caller,
        },
    )

    if decision.get("decision") == "forward":
        try:
            resp = requests.post(
                PYTHON_ENGINE_URL,
                json={
                    "query": user_msg,
                    "session_id": request.session_id,
                    "allow_web": bool(request.allow_web),
                    "context": {
                        **(request.context or {}),
                        "caller": request.caller,
                        "bridge_source": request.source,
                        "trace_id": trace_id,
                    },
                },
                headers=_build_engine_headers(request.caller),
                timeout=10,
            )
            resp.raise_for_status()
            engine_data = resp.json()

            answer = _extract_answer(engine_data)
            if not answer:
                decision = {
                    "decision": "block",
                    "verification_status": "UNVERIFIED",
                    "reason": "Python engine response not verifiable.",
                    "data": {"response_content": ""},
                }
            else:
                verification_status = str(engine_data.get("verification_status") or "UNVERIFIED").upper()
                truth_declaration = (
                    "VERIFIED"
                    if verification_status == "VERIFIED"
                    else "VERIFIED_PARTIAL"
                    if verification_status == "PARTIAL"
                    else "UNVERIFIED"
                )
                formatted_response = (
                    "Based on verified source: Python UniGuru engine"
                    if verification_status == "VERIFIED"
                    else "This information is partially verified from: Python UniGuru engine"
                    if verification_status == "PARTIAL"
                    else "Verification status: UNVERIFIED"
                )
                decision = {
                    "decision": engine_data.get("decision", "answer"),
                    "reason": engine_data.get("reason", "Response provided by Python UniGuru engine."),
                    "verification_status": verification_status,
                    "status_action": engine_data.get("status_action"),
                    "governance_flags": engine_data.get("governance_flags", {}),
                    "governance_output": engine_data.get("governance_output", {}),
                    "ontology_reference": engine_data.get("ontology_reference"),
                    "reasoning_trace": engine_data.get("reasoning_trace"),
                    "data": {
                        "response_content": answer,
                        "verification": {
                            "source_name": "Python UniGuru engine",
                            "truth_declaration": truth_declaration,
                            "formatted_response": formatted_response,
                        },
                        "engine_response": engine_data,
                    },
                    "forwarded_to": PYTHON_ENGINE_URL,
                }

        except Exception as exc:
            decision = {
                "decision": "block",
                "verification_status": "UNVERIFIED",
                "reason": f"Python engine unavailable: {str(exc)}",
                "data": {"response_content": ""},
            }

    sealed_response = enforcer.process_and_seal(decision, trace_id)

    if not enforcer.verify_bridge_seal(sealed_response):
        raise HTTPException(status_code=500, detail="Enforcement Seal Violation: Tampering Detected.")

    latency = (time.time() - start_time) * 1000
    sealed_response["latency_ms"] = round(latency, 2)
    sealed_response["trace_id"] = trace_id

    return sealed_response


@app.post("/integrations/gurukul/chat")
async def gurukul_chat(request: GurukulQueryRequest):
    if not request.student_query.strip():
        raise HTTPException(status_code=400, detail="student_query is required.")
    return gurukul_adapter.process_student_query(request)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "bridge_version": "3.0.0",
        "python_engine_target": PYTHON_ENGINE_URL,
        "external_llm_calls": bool(os.getenv("UNIGURU_LLM_URL")),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
