@echo off
TITLE UniGuru FastAPI Backend (Port 8000)
cd /d "%~dp0"
echo ==========================================================
echo Starting UniGuru FastAPI Backend (Port 8000)
echo Connected to: http://127.0.0.1:8001/generate
echo ==========================================================
set PYTHONPATH=.;backend
set UNIGURU_HOST=127.0.0.1
set UNIGURU_PORT=8000
set UNIGURU_API_AUTH_REQUIRED=false
set UNIGURU_DEMO_AUTH_ENABLED=true
set UNIGURU_ALLOWED_CALLERS=*
set UNIGURU_LLM_URL=http://127.0.0.1:8001/generate
set NO_PROXY=*
set HTTP_PROXY=
set HTTPS_PROXY=
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe -m uvicorn service.api:app --host 127.0.0.1 --port 8000 --reload
) else (
    python -m uvicorn service.api:app --host 127.0.0.1 --port 8000 --reload
)
pause

