@echo off
TITLE UniGuru Local LLM Service (Port 8001)
cd /d "C:\Ganesh_149\uniguru\bhiv-uniguru"
echo ==========================================================
echo Starting UniGuru Local Fine-Tuned Model Server (Port 8001)
echo Model: models\adapters\qwen2.5-7b-indic-squad-mr-remediated
echo ==========================================================
"C:\Ganesh_149\uniguru\bhiv-uniguru\venv\Scripts\python.exe" inference\serve_local_llm.py --model models\adapters\qwen2.5-7b-indic-squad-mr-remediated --port 8001
pause

