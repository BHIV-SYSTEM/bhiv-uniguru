@echo off
TITLE UniGuru Local LLM Service (Port 8001)
cd /d "%~dp0"

set "MODEL_DIR=models\adapters\qwen2.5-7b-indic-squad-mr-remediated"
set "WEIGHTS_FILE=%MODEL_DIR%\adapter_model.safetensors"

echo ==========================================================
echo Starting UniGuru Local Fine-Tuned Model Server (Port 8001)
echo Target Model: %MODEL_DIR%
echo ==========================================================

:: Select Python interpreter
if exist "venv\Scripts\python.exe" (
    set "PYTHON_CMD=venv\Scripts\python.exe"
) else (
    set "PYTHON_CMD=python"
)

:: Check if fine-tuned weights exist. If missing, automatically download them from Hugging Face!
if not exist "%WEIGHTS_FILE%" (
    echo [INFO] Fine-tuned model weights not found at:
    echo        %WEIGHTS_FILE%
    echo [INFO] Downloading weights from Hugging Face (shivam159/qwen2.5-7b-marathi-indic-squad)...
    echo.
    %PYTHON_CMD% -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='shivam159/qwen2.5-7b-marathi-indic-squad', local_dir='%MODEL_DIR%')"
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] Failed to download model weights from Hugging Face!
        echo Please check your internet connection or download manually to:
        echo %MODEL_DIR%
        pause
        exit /b 1
    )
    echo [SUCCESS] Model weights downloaded and verified successfully!
    echo.
) else (
    echo [INFO] Fine-tuned model weights verified and ready.
)

echo Starting inference server on port 8001...
%PYTHON_CMD% inference\serve_local_llm.py --model "%MODEL_DIR%" --port 8001
pause

