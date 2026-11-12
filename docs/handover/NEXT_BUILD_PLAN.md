# UniGuru Next-Build Plan (Hypervelocity Increments)

**Document Version:** 1.0.0  
**Date:** 2026-11-12  
**Task ID:** UG-HO-01  
**Operating Cadence:** BHIV Hypervelocity Daily Delivery (180–360 min increments)  
**Lead Engineer:** Vijay Dhawan  

---

## 1. Operating Model & Selection Rationale

Following the BHIV/BHQ hypervelocity standard, development shifts from prolonged unverified feature development to short, evidence-based, independently deliverable increments. Each increment is assigned a single accountable builder, an explicit outcome, verifiable acceptance criteria, explicit dependencies, and reproducible evidence requirements.

The three tasks below address the highest-leverage operational gaps identified in the UG-HO-01 audit:
1. **Public Cloud Availability** (Fixing the dead Render deployment).
2. **Repository Integrity & Build Portability** (Purging the 200MB duplicate tree and fixing Vite path issues).
3. **Core Curriculum Recall Expansion** (Expanding textbook coverage from 4 to 12 books).

---

## 2. Increment Specifications

### Task 1: UG-BL-01 - Public Render Deployment & Health Monitoring
- **Priority:** **P0 (Critical Blocker)**
- **Accountable Owner:** Vijay Dhawan (Infrastructure Lead)
- **Estimated Effort:** 180–240 minutes
- **Outcome:** A live, publicly accessible, high-availability deployment of UniGuru API on Render (`https://uniguru-v2.onrender.com`), protected by automated keepalive health pings.
- **Scope & Implementation Steps:**
  1. Link Render service `uniguru-api` to the verified handover branch (`ug-ho-01-infrastructure-handover`).
  2. Configure Render environment variables matching `docs/handover/INFRASTRUCTURE_BASELINE.md`.
  3. Trigger zero-downtime Docker container build using root `Dockerfile`.
  4. Implement an automated 10-minute GitHub Action or external probe (`GET /health`) to prevent free-tier container sleep.
  5. Validate public HTTPS connectivity from external networks.
- **Acceptance Criteria:**
  - `GET https://uniguru-v2.onrender.com/health` returns `200 OK` in <500ms with `status: "ok"`.
  - `GET https://uniguru-v2.onrender.com/health/ready` returns `200 OK`.
  - `POST https://uniguru-v2.onrender.com/new_query` rejects unauthenticated calls (`401`) and accepts authenticated Mitra calls (`200`).
  - Zero downtime observed over a continuous 4-hour test window.
- **Dependencies:** Authorized Render dashboard access; handover branch pushed to Central Depository.
- **Evidence Requirements:**
  - Public cURL request/response transcripts from an external machine.
  - Render build console logs.
  - SSL/TLS certificate verification output.

---

### Task 2: UG-BL-02 - Repository Tree De-Duplication & Build Remediation
- **Priority:** **P1 (Technical Debt)**
- **Accountable Owner:** Vijay Dhawan / Isha Singh
- **Estimated Effort:** 180–240 minutes
- **Outcome:** Clean, standardized Git tree without the 200MB nested `bhiv-uniguru-main/` folder; full frontend build portability across all directory naming conventions.
- **Scope & Implementation Steps:**
  1. Create a dedicated cleanup branch `chore/repo-dedup-cleanup`.
  2. Perform `git rm -r --cached bhiv-uniguru-main/` to remove the redundant nested project tree.
  3. Verify that no root imports or docker builds reference paths inside `bhiv-uniguru-main/`.
  4. Refactor `frontend/index.html` by extracting inline `<style>` tags into `src/initial-loader.css`, resolving Vite's path resolution failure on folders containing parentheses.
  5. Run `npm run build` and `pytest` to confirm zero regression.
  6. Submit clean, single-purpose Pull Request to `main`.
- **Acceptance Criteria:**
  - Root directory contains exactly one copy of backend, frontend, curriculum, and tests.
  - Repository git clone size reduced by >200MB.
  - `npm run build` succeeds on any directory name (including paths with spaces and parentheses).
  - All 467 tests in test baseline pass.
- **Dependencies:** Task `UG-HO-01` baseline established.
- **Evidence Requirements:**
  - Git tree manifest (`git ls-tree -r HEAD`).
  - Full test run log (467 passed).
  - Frontend production build output (`dist/` generated without error).

---

### Task 3: UG-BL-03 - Balbharati Curriculum Expansion (Grades 6–10)
- **Priority:** **P1 (Capability & Recall)**
- **Accountable Owner:** Vinayak / Knowledge Lead
- **Estimated Effort:** 240–360 minutes
- **Outcome:** Expand Balbharati Maharashtra State Board coverage from 4 textbooks (37 Kosha entries) to 12 textbooks (>150 Kosha entries), dramatically reducing out-of-syllabus abstentions.
- **Scope & Implementation Steps:**
  1. Stage licensed Balbharati PDFs for Grades 6–10 (General Science, History & Civics, Geography).
  2. Run `scripts/ingest_balbharti_masterdb.py` to extract chapters, concept boundaries, and pedagogical glossaries.
  3. Generate canonical Kosha JSON records under `backend/data/kosha/`.
  4. Rebuild the FAISS dense index (`backend/RAG/chunks_v4.db`).
  5. Execute `backend/scripts/evaluate_rag_retrieval.py` against the 100-case evaluation benchmark.
- **Acceptance Criteria:**
  - Ingested textbooks increased from 4 to 12.
  - Active Kosha knowledge entries increased from 37 to >150.
  - Retrieval benchmark accuracy exceeds 92% (up from 84%).
  - Grounding integrity maintained (100% of generated answers contain valid textbook page and chapter citations).
- **Dependencies:** Balbharati digital PDF assets.
- **Evidence Requirements:**
  - Ingestion run report (`curriculum/ingestion_proof.json`).
  - Updated `verified_textbook_registry.json`.
  - Retrieval benchmark JSON report (`tests/evaluation_100_results.json`).

---

## 3. Execution Schedule & Milestone Tracking

| Milestone | Task | Planned Start | Target Delivery | Dependency |
|---|---|---|---|---|
| **M1: Cloud Parity** | UG-BL-01 | T + 0 hr | T + 4 hr | UG-HO-01 Handover PR |
| **M2: Tree Sanitization** | UG-BL-02 | T + 4 hr | T + 8 hr | UG-BL-01 Verified |
| **M3: Knowledge Expansion** | UG-BL-03 | T + 8 hr | T + 14 hr | UG-BL-02 Merged |
