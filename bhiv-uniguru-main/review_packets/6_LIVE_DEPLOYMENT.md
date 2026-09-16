# LIVE DEPLOYMENT STRATEGY (Vercel & Render)

## 1. Frontend (Vite/React) -> Vercel
The frontend is fully configured for Vercel deployment.
- **Config**: `vercel.json` natively handles SPA routing structure for React Router.
- **Environment**: You must expose `VITE_API_URL`, pointing to your backend's external URL, inside your Vercel Project Settings interface.
- **Build Command**: `tsc -b && vite build` (Automatically mapped in `package.json`).

## 2. Backend (FastAPI / Kosha) -> Render
The FastAPI server is built asynchronously and can be pushed gracefully to Render.
- **Requirements**: `requirements.txt` maps all required libraries (`uvicorn`, `fastapi`, `pydantic`, `groq`, `requests`).
- **Start Command**: `uvicorn service.api:app --host 0.0.0.0 --port 10000`
- **Integrations**: Make sure to import your `.env` variables (like `UNIGURU_LLM_API_KEY`, `SUPABASE_ANON_KEY`, `GROQ_API_KEY`, `EXTERNAL_API_SECRET_KEY`) directly into the Render Environment panel.

## 3. Data Sync Strategy
Because the backend now scans `backend/data/kosha/` automatically on runtime, you can either:
1. Commit your definitive JSON datasets to Github directly inside that directory so the server scales statistically.
2. Hook an S3 bucket or external volume up to that path for dynamic updating down the line.
