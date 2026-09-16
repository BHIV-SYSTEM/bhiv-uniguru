# UniGuru Execution Flow

## End-to-End Path
`UI -> Node Middleware -> Python /ask -> ConversationRouter -> Engine/LLM -> Response`

## Detailed Steps
1. UI or client sends query to Node middleware (`/api/v1/chat/query`).
2. Node normalizes payload and caller context.
3. Node forwards request to Python `POST /ask`.
4. Python API validates request and enriches context.
5. `ConversationRouter` classifies query:
   - `ROUTE_UNIGURU` for deterministic knowledge path
   - `ROUTE_LLM` for open/general queries
   - `ROUTE_WORKFLOW` for workflow/tool requests
   - `ROUTE_SYSTEM` for blocked system-command requests
6. Response is sealed with governance/trace metadata and returned upstream.
7. If any stage fails, safe fallback response is returned with `UNVERIFIED`.

## Safety Notes
- Queue saturation returns a fallback answer, not `503`.
- Missing auth token in demo mode does not crash the system.
- Missing KB or LLM endpoint still returns a non-empty response.
