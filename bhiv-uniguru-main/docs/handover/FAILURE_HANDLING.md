# Failure Handling

## Design Rule
UniGuru must always return a response payload for query paths.

## Failure Matrix
1. Missing API token:
   - If auth is required and caller token is invalid, `/ask` degrades to safe fallback payload.
2. Missing KB files/index:
   - KB loader skips invalid files and returns no-match behavior.
   - Router falls back to LLM route.
3. LLM endpoint missing or failing:
   - Router serves internal demo response (`internal://demo-llm` behavior).
4. Queue saturation:
   - API returns safe fallback answer with `UNVERIFIED`.
5. STT unavailable:
   - `/voice/query` returns safe fallback.

## Retrieval Confidence Gate
- KB answers are accepted only when retrieval confidence passes `UNIGURU_KB_CONFIDENCE_THRESHOLD` (default `0.45`).
- If confidence is below threshold, router falls through to `ROUTE_LLM` and then safe fallback if LLM fails.

## Final Fallback Message
`I am still learning this topic, but here is a basic explanation...`

## Operational Checks
- `GET /health`
- `GET /ready`
- `python test/run_phase8_validation.py`
