# UniGuru frontend deployment

## Configured production targets

- Frontend API base URL: `https://complete-uniguru.onrender.com` (`VITE_API_BASE_URL` in `.env.production`).
- Frontend origin configured for backend CORS: `https://uni-guru.vercel.app` (`UNIGURU_CORS_ORIGINS`).
- Render API service name in `render.yaml`: `complete-uniguru`.

These are repository configuration values. They do not establish that either deployment is currently live; complete the live browser verification before acceptance.

## Required deployment configuration

Set `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `UNIGURU_API_TOKEN`, and `UNIGURU_API_TOKENS` in the deployment secret store. Configure the production frontend origin in `UNIGURU_CORS_ORIGINS`. Production startup fails if the required Supabase auth provider or CORS origin is missing.

Chat storage uses `UNIGURU_CHAT_DB_PATH` under `/var/lib/uniguru`; the deployment must mount persistent storage at that path. Do not place secrets in committed environment files.

The Render Blueprint declares a Starter web service because Render persistent disks require a paid service. A disk-attached service runs as a single instance; confirm the applicable Render price and scaling constraints before applying the Blueprint. This repository change does not deploy or provision a paid resource.

The production Docker image starts `backend/main.py`, which mounts the runtime API under `/v2`. Do not replace this with a direct `uvicorn service.api:app` command unless the runtime mount is also preserved.
The Docker build context excludes `.env*` files; supply production values through Render or the deployment environment, not image layers.

MDU validation is an optional ecosystem integration, not a startup dependency for the normal UniGuru API. Render explicitly sets `MDU_ENABLED=false`; when disabled, the runtime produces local schema/provenance validation and skips authenticated MDU requests. To enable live MDU validation, first obtain provider confirmation that the historical credential has been revoked, then supply a replacement `MDU_API_KEY` through the deployment secret store and set `MDU_ENABLED=true`.

## Environment modes

- **Local development:** Start the API and frontend with `backend/.env.example` and local service URLs. Development CORS origins are localhost only.
- **Local demo:** Use demo authentication only when explicitly enabled for a non-production, non-Render environment. Never copy demo credentials into production.
- **Test:** Tests use isolated fixtures/mocks and do not establish production authentication, external service access, or deployment readiness.
- **Production:** Set `UNIGURU_ENVIRONMENT=production`, keep demo authentication disabled, configure real Supabase and API auth values in the secret store, use the production CORS origin, and mount durable chat storage at `/var/lib/uniguru`. The current API renders a local internal demo LLM fallback unless an actual production LLM endpoint is configured; readiness reports this fallback as available, so `/ready` alone does not prove a live model dependency.

## Local development

Use `backend/.env.example` as a template. Local demo authentication is disabled by default; it can only be enabled explicitly with `UNIGURU_DEMO_AUTH_ENABLED=true` outside production. The normal local frontend API default remains `http://127.0.0.1:8000`.

## Verification

After deployment, verify the UI URL, authentication, a chat query, browser CORS preflight/API response, durable history after service restart, and user-to-user access denial. Store timestamped results with the deployed commit and version in the Buyer Evidence Pack.
