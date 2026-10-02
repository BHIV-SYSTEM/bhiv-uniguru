# FAQ

1. What happens if token is missing?
   - In demo mode (`UNIGURU_API_AUTH_REQUIRED=false`), requests still run.
   - In strict mode, `/ask` degrades safely instead of crashing.

2. What if KB files are missing?
   - Router shifts to LLM/fallback path and still returns an answer.

3. What if KB index JSON is broken?
   - Index load failure is handled; system continues with empty index.

4. What if LLM endpoint is not configured?
   - Internal demo LLM fallback remains available.

5. What if LLM endpoint is configured but down?
   - Router catches failure and serves safe fallback answer.

6. Why is response marked `UNVERIFIED`?
   - KB verification failed or fallback mode was used.

7. How do I force strict auth?
   - Set `UNIGURU_API_AUTH_REQUIRED=true` and provide `UNIGURU_API_TOKEN` or `UNIGURU_API_TOKENS`.

8. How do I change LLM model?
   - Update `UNIGURU_LLM_MODEL`.

9. How do I change LLM endpoint?
   - Update `UNIGURU_LLM_URL`.

10. Where is the canonical backend entrypoint?
   - [`backend/main.py`](/c:/Users/Yass0/OneDrive/Desktop/TASK14/backend/main.py) and `run/run_backend.*`.

11. Where is the canonical Node entrypoint?
   - [`node-backend/src/server.js`](/c:/Users/Yass0/OneDrive/Desktop/TASK14/node-backend/src/server.js) and `run/run_node.*`.

12. How do I run full validation in one command?
   - `python test/run_phase8_validation.py`

13. Where are test outputs saved?
   - [`demo_logs/phase8_test_outputs.json`](/c:/Users/Yass0/OneDrive/Desktop/TASK14/demo_logs/phase8_test_outputs.json)

14. Can the system return 503 during demo queries?
   - Query paths are designed to return fallback `200` payloads instead.

15. How do I onboard a new developer quickly?
   - Start with:
     - [`docs/architecture/SYSTEM_OVERVIEW.md`](/c:/Users/Yass0/OneDrive/Desktop/TASK14/docs/architecture/SYSTEM_OVERVIEW.md)
     - [`docs/architecture/EXECUTION_FLOW.md`](/c:/Users/Yass0/OneDrive/Desktop/TASK14/docs/architecture/EXECUTION_FLOW.md)
     - [`docs/handover/SETUP_GUIDE.md`](/c:/Users/Yass0/OneDrive/Desktop/TASK14/docs/handover/SETUP_GUIDE.md)
