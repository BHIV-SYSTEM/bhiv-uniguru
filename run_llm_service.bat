@echo off
TITLE UniGuru Local LLM Service (Port 8001)
cd /d "%~dp0"
echo ==========================================================
echo Starting UniGuru Local Fine-Tuned Model Server (Port 8001)
echo Model: models\adapters\qwen2.5-7b-indic-squad-mr-remediated
echo ==========================================================
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe inference\serve_local_llm.py --model models\adapters\qwen2.5-7b-indic-squad-mr-remediated --port 8001
) else (
    python inference\serve_local_llm.py --model models\adapters\qwen2.5-7b-indic-squad-mr-remediated --port 8001
)
pause

