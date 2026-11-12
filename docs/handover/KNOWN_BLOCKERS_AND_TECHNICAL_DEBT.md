# UniGuru Known Blockers & Technical Debt

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-12  
**Task ID:** UG-HO-01  
**Classification:** Engineering Handover Risk Register  
**Lead Engineer:** Vijay Dhawan  

---

## 1. Severity Classification Matrix

| ID | Issue Description | Severity | Status | Workaround / Mitigation | Target Task |
|---|---|---|---|---|---|
| **BLK-01** | Public Render Deployment Offline / Timed Out | **P0** | Active Blocker | Run locally on `127.0.0.1:8000`; redeploy Docker on Render | UG-BL-01 |
| **DEBT-01** | Accidental Nested `bhiv-uniguru-main/` Folder in Git | **P1** | Active Debt | Authoritative code is at root; exclude nested tree | UG-BL-02 |
| **DEBT-02** | In-Memory Rate Limiter Tripping Full Test Suite | **P1** | Known Caveat | Set `UNIGURU_RATE_LIMIT_MAX_REQUESTS=10000` during tests | Handover Config |
| **DEBT-03** | Vite Build Fails on Paths Containing Parentheses | **P2** | Environment Bug | Pre-built in `dist/`; move inline CSS to external file | UG-BL-02 |
| **DEBT-04** | Limited Balbharati Textbook Coverage (37 entries) | **P2** | Coverage Gap | Abstains cleanly; expand ingestion to Grades 6-10 | UG-BL-03 |
| **DEBT-05** | External LLM Fallback Dependent on Groq API | **P3** | Architecture Gap | Abstention is safe; implement local small model (Ollama) | Backlog |
| **DEBT-06** | BHIV Ecosystem Services File-Backed Locally | **P3** | Integration Limit | Mock contracts verified; configure cloud VPC endpoints | Backlog |

---

## 2. Detailed Technical Audit of Issues

### 2.1 BLK-01: Public Render Deployment Offline (P0)
- **Observed Symptom:** Probing `https://uniguru-v2.onrender.com/health` and `https://complete-uniguru.onrender.com/health` results in connection timeout after 10,000ms.
- **Root Cause:** Free-tier or inactive Render service spun down; DNS points to Render ingress which drops connections when backend container is not listening.
- **Engineering Risk:** External clients (Mitra, TANTRA, student frontend) cannot reach the service in cloud environments.
- **Resolution Plan:** Execute Task `UG-BL-01` to manually redeploy the Docker image via Render dashboard connected to branch `ug-ho-01-infrastructure-handover`.

### 2.2 DEBT-01: Accidental Nested `bhiv-uniguru-main/` Subdirectory (P1)
- **Observed Symptom:** Root contains a nested subdirectory `bhiv-uniguru-main/` tracked in git with duplicate source code, docs, and test files.
- **Root Cause:** In git commit `95ea851`, an engineer committed a nested copy of the entire project repository.
- **Engineering Risk:** New developers may inadvertently edit files in `bhiv-uniguru-main/backend/...` instead of the root `backend/...`, causing silent divergence. Git clone and pull times are doubled.
- **Resolution Plan:** Scheduled for Task `UG-BL-02`. Remove the entire nested tree via `git rm -r bhiv-uniguru-main/` in a dedicated clean PR.

### 2.3 DEBT-02: Test Suite Rate Limiter Collision (P1)
- **Observed Symptom:** Running `pytest` across all 124 tests in `tests/test_e2e_integration.py` causes 7 tests to fail with `HTTP 429 Too Many Requests`.
- **Root Cause:** `backend/service/api.py` enforces a sliding-window rate limit of 60 requests per 60 seconds per IP. Because `test_rate_limiting_enforcement` rapidly fires 30 requests in a loop, subsequent tests in the same test runner run exceed the 60-request quota on `127.0.0.1`.
- **Resolution Plan:** Configure `pytest.ini` with `env = UNIGURU_RATE_LIMIT_MAX_REQUESTS=10000` or export the environment variable before invoking test runners. When elevated, 100% of tests (467/467) pass.

### 2.4 DEBT-03: Vite HTML Inline Proxy Path Resolution Bug (P2)
- **Observed Symptom:** Running `npm run build` inside `frontend/` fails with:
  `[vite:html-inline-proxy] Could not load .../bhiv-uniguru-main (1)/frontend/index.html?html-proxy&inline-css&index=0.css`.
- **Root Cause:** Vite 5.4.21 has a known bug on Windows where paths containing spaces and parentheses ` (1)` cause the internal Rollup URL decoder to fail to match inline `<style>` blocks in `index.html`.
- **Resolution Plan:** The production assets in `frontend/dist/` are currently verified and operational. The permanent fix is to extract the 30 lines of CSS in `frontend/index.html` into a standalone `src/initial-loader.css` file.

### 2.5 DEBT-04: Limited Textbook Knowledge Base Ingestion (P2)
- **Observed Symptom:** Queries on Marathi literature, Grade 9 Civics, or Grade 8 Mathematics return `NO_VERIFIED_KNOWLEDGE` or fallback to general reasoning.
- **Root Cause:** Only 4 Balbharati textbooks (37 Kosha knowledge entries) have been transformed into structured knowledge graphs.
- **Resolution Plan:** Execute Task `UG-BL-03` to batch ingest 8 additional textbooks from Balbharati Maharashtra State Board.

### 2.6 DEBT-05: External LLM Dependency (P3)
- **Observed Symptom:** When a query falls outside the curriculum and is routed to `ROUTE_LLM`, the response fails if `GROQ_API_KEY` is not present in `.env`.
- **Mitigation:** The system safely returns a controlled message ("I couldn't get a response from the configured language-model provider") without crashing or corrupting sessions.

### 2.7 DEBT-06: File-Backed Ecosystem Integration Points (P3)
- **Observed Symptom:** TANTRA, MDU, and Bucket telemetry integration tests validate schema contracts against local proof files in `review_packets/proof_logs/`.
- **Mitigation:** Interfaces are architecturally compliant; live RPCs will be connected once the BHIV cluster network routing and credentials are provided.
