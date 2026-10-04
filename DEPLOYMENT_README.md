# UniGuru Docker + CI/CD

Repository: BHIV-SYSTEM/bhiv-uniguru

## Local
1. Copy `.env.example` to `.env`.
2. Run `docker compose up -d --build`.
3. Open `http://localhost:8020`.
4. Health: `curl http://localhost:8020/health`.

## Production
Images:
- `bhiv/uniguru-api:<7-char-git-sha>`
- `bhiv/uniguru-frontend:<7-char-git-sha>`

Production Compose publishes Nginx on `UNIGURU_HTTP_PORT`, default `8026`.

## Required GitHub Actions secrets
`DOCKER_USERNAME`, `DOCKER_PASSWORD`, `VM_IP`, `VM_PORT`, `VM_USERNAME`, `VM_PASSWORD`, `VM_APP_DIR`, `UNIGURU_ENV_FILE`, `UNIGURU_FRONTEND_API_BASE_URL`, `UNIGURU_FRONTEND_BACKEND_URL_V1`, `UNIGURU_FRONTEND_GOOGLE_OAUTH_URL`, `UNIGURU_GOOGLE_CLIENT_ID`.

`UNIGURU_FRONTEND_API_BASE_URL` must be the browser-visible public origin, such as `http://SERVER_IP:8026` or your HTTPS domain. The Nginx config routes the React app's `/user`, `/chat`, `/guru`, `/auth`, `/feature`, `/ask`, `/new_rag`, `/new_query`, and `/v2` requests to FastAPI.

`UNIGURU_ENV_FILE` is the server-side environment file and should contain real secrets only in GitHub Actions, not in Git.

## Deployment flow
main push -> Compose validation -> frontend build validation -> Docker Hub build/push -> VM archive transfer -> SHA-tagged deploy -> API/frontend/public health checks -> release history. Failed deployment triggers automatic rollback to the last `SUCCESS` or `ROLLBACK_SUCCESS` SHA.

## Security note
The repository currently has environment files containing credential-like values. Do not propagate them into new deployment files. Rotate exposed credentials and keep production values in GitHub/VM secret storage.
