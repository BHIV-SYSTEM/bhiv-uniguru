# UniGuru System Overview

## What UniGuru Is
UniGuru is a resilient knowledge-and-conversation backend designed for demo-safe operation.  
It answers user queries through deterministic knowledge retrieval first, then LLM routing, and finally guaranteed safe fallback.

## Core Principles
- Never return a blank response.
- Never rely on a single dependency path.
- Keep routing and failure behavior observable and documented.

## Runtime Components
- `frontend/`: UI client (optional in API-only deployments).
- `node-backend/`: Middleware entry for product APIs (`/api/v1/chat/query`, `/api/v1/gurukul/query`).
- `backend/uniguru/service/api.py`: Canonical Python API (`POST /ask`).
- `backend/uniguru/router/conversation_router.py`: Route selection (`ROUTE_UNIGURU`, `ROUTE_LLM`, `ROUTE_WORKFLOW`, `ROUTE_SYSTEM`).
- `backend/uniguru/core/`: Deterministic rule engine and governance.
- `backend/uniguru/retrieval/`: KB and web retrieval paths.
- `backend/uniguru/integrations/`: Telemetry, language adapter, core-reader integrations.

## Guaranteed Response Contract
For every query:
1. KB hit: return deterministic knowledge answer.
2. KB miss: route to LLM path.
3. LLM failure: return safe fallback:
   `I am still learning this topic, but here is a basic explanation...`

## Canonical Entry Points
- Backend: `backend/main.py` or `run/run_backend.sh`
- Node middleware: `run/run_node.sh`
- End-to-end validation: `python test/run_phase8_validation.py`
