# UniGuru System Wiring Report

## Architecture Diagram

```text
User / Frontend
  -> Node UniGuru Backend (Express, :8001)
    -> Bridge Middleware (FastAPI, :8002, POST /chat)
      -> Python UniGuru Engine (FastAPI, :8000, POST /ask)
        -> Conversation Router
          -> Local KB / Reasoning Engine / LLM fallback / Governance
      <- sealed response
    <- aiResponse payload
  <- frontend render

Student UI
  -> Gurukul Backend (FastAPI, :8003, POST /api/v1/chat/ask)
    -> UniGuru Python Engine (POST /ask)
  <- answer for Gurukul frontend
```
Frontend / User
  ↓
Node UniGuru Backend (8001)
  ↓
Bridge Middleware (8002)
  ↓
Python UniGuru Engine / FastAPI (8000)
  ↓
Router
  ↓
Reasoning Engine / Knowledge Base / LLM
  ↓
Response to Bridge
  ↓
Response to Node
  ↓
Response to User

Student UI
  ↓
Gurukul Backend (8003)
  ↓
UniGuru /ask (8000)
  ↓
Response to Gurukul


## Port Configuration

| Service | Port | Entry |
| --- | --- | --- |
| Python UniGuru Engine | 8000 | `/ask`, `/health` |
| Node UniGuru Backend | 8001 | `/api/v1/chat/new`, `/health` |
| Bridge Middleware | 8002 | `/chat`, `/health` |
| Gurukul Backend | 8003 | `/api/v1/chat/ask`, `/health` |

## Service Endpoints

- Node backend now forwards chat traffic to `UNIGURU_BRIDGE_URL` and returns the bridge result in the existing `aiResponse` contract.
- Bridge middleware now forwards reasoning requests to `UNIGURU_ENGINE_URL` with caller context and service-token auth.
- Python router now uses `UNIGURU_LLM_URL` for general conversation when the LLM route is selected.
- Gurukul backend forwards student queries to `POST /ask` with `caller=gurukul-platform`, `student_id`, and optional class/session context.

## Wiring Changes

- Replaced the mock response in `Complete-Uniguru/server/controller/chatController.js` with a real bridge call.
- Updated the Node backend default port to `8001`.
- Updated frontend default API base URL to `http://localhost:8001`.
- Rewired `uniguru/bridge/server.py` to call the local Python `/ask` engine instead of a legacy/mock backend.
- Activated environment-driven LLM delegation in `uniguru/router/conversation_router.py`.
- Added Gurukul backend route implementation in `uniguru_backend/app.py`.
- Added verified Gurukul KB metadata and rebuilt the runtime index.

## Test Results

| Test | Result | Notes |
| --- | --- | --- |
| Python syntax compile | PASS | `uniguru/bridge/server.py`, `uniguru/router/conversation_router.py`, `uniguru_backend/app.py` |
| Router tests | PASS | `pytest tests/test_conversation_router.py -q` -> `6 passed` |
| Node syntax check | PASS | `node --check` on `chatController.js` and `server.js` |
| Bridge smoke test | PASS | Mocked `/chat` forwarding returned `200`, `PARTIAL`, bridged answer |
| Gurukul backend smoke test | PASS | Mocked `/api/v1/chat/ask` returned `200`, `ROUTE_UNIGURU` |
| KB rebuild | PASS | `knowledge/index/runtime_manifest.json` now records 3 Gurukul documents |

## Notes

- `ChatContainer.tsx` already contains active send-message logic in the current workspace, so no uncomment patch was required there.
- Full live end-to-end HTTP execution across all four running services was not performed in this turn because the stack was not started together; the integration was validated through syntax checks, unit tests, KB rebuild, and mocked API smoke tests.
