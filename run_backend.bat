@echo off
TITLE UniGuru FastAPI Backend (Port 8000)
cd /d "C:\Ganesh_149\uniguru\bhiv-uniguru"
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
"C:\Ganesh_149\uniguru\bhiv-uniguru\venv\Scripts\python.exe" -m uvicorn service.api:app --host 127.0.0.1 --port 8000 --reload
pause

