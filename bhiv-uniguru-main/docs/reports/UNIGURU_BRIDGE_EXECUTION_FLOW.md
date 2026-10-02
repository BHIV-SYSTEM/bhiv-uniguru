# UniGuru Bridge Execution Flow

Date: 2026-03-19

## Objective

Show exactly how Node and Python services interact for BHIV product and Gurukul traffic.

## Product Path (Frontend -> Node -> UniGuru)

1. Frontend sends:
   - `POST /api/v1/chat/query`
   - Body: `{ "query": "...", "session_id": "...", "context": { ... } }`
2. Node middleware (`node-backend/src/server.js`) enforces:
   - caller = `bhiv-assistant`
3. Node request builder (`node-backend/src/uniguruClient.js`) produces:
```json
{
  "query": "...",
  "context": {
    "caller": "bhiv-assistant"
  },
  "session_id": "...",
  "allow_web": false
}
```
4. Node forwards to Python:
   - `POST /ask` on `uniguru-api`
5. Python `/ask` validates:
   - service token (if enabled)
   - caller allowlist
   - payload schema
6. Router executes and returns contract response with:
   - `decision`
   - `verification_status`
   - `routing`
   - `ontology_reference`
   - `core_alignment`
7. Node returns response to product client in `data`.

## Gurukul Path (Gurukul -> Node -> UniGuru)

1. Gurukul sends:
   - `POST /api/v1/gurukul/query`
   - Body includes `student_query`, `student_id`
2. Node middleware enforces:
   - caller = `gurukul-platform`
3. Node forwards to `/ask` with:
```json
{
  "query": "student_query",
  "context": {
    "caller": "gurukul-platform",
    "student_id": "..."
  }
}
```
4. Python validates caller and processes deterministically.
5. Node returns structured Gurukul response envelope.

## Bridge Error Behavior

- Empty query -> `502` from Node with explicit integration error message.
- Upstream UniGuru timeout/error -> `502` from Node.
- Invalid caller in Python -> `403`.
- Missing/invalid token when auth enabled -> `401`.

## Files

- `node-backend/src/server.js`
- `node-backend/src/uniguruClient.js`
- `backend/uniguru/service/api.py`
- `deploy/nginx/conf.d/uniguru.conf`
