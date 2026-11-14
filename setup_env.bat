@echo off
setlocal enabledelayedexpansion

echo ==============================================================================
echo  UniGuru Qwen 2.5 7B QLoRA Fine-Tuning Environment Setup (Windows Native)
echo  Target Hardware: NVIDIA GeForce RTX 3060 (12GB VRAM)
echo  Target Stack: Python 3.10 - 3.12 ^| PyTorch 2.5.1+cu121 ^| CUDA 12.1
echo ==============================================================================
echo.

:: 1. Verify NVIDIA GPU & Driver
echo [1/6] Checking NVIDIA GPU and driver...
where nvidia-smi >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] 'nvidia-smi' was not found in PATH.
    echo If this is your 2GB development machine, you can run dry-run validation only.
    echo If this is the RTX 3060 training machine, ensure the NVIDIA Game Ready or Studio Driver is installed.
) else (
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
)
echo.

:: 2. Detect Compatible Python Version (3.10, 3.11, or 3.12 required for PyTorch cu121 & Unsloth)
echo [2/6] Detecting compatible Python installation...
set "PY_CMD="

:: Check Python launcher for 3.11, 3.10, 3.12
py -3.11 --version >nul 2>nul && set "PY_CMD=py -3.11"
if not defined PY_CMD (
    py -3.10 --version >nul 2>nul && set "PY_CMD=py -3.10"
)
if not defined PY_CMD (
    py -3.12 --version >nul 2>nul && set "PY_CMD=py -3.12"
)
if not defined PY_CMD (
    python --version >nul 2>nul && set "PY_CMD=python"
)

if not defined PY_CMD (
    echo [ERROR] No Python installation detected!
    echo Please install Python 3.10 or 3.11 from https://www.python.org/
    exit /b 1
)

echo Using Python interpreter: %PY_CMD%
%PY_CMD% -c "import sys; print('Detected version:', sys.version); v = sys.version_info; sys.exit(0 if (3, 10) <= (v.major, v.minor) <= (v.minor if v.major == 3 and v.minor <= 12 else 12) else 2)"
if %errorlevel% equ 2 (
    echo [WARNING] Current Python version is not in the recommended range [3.10 - 3.12].
    echo PyTorch 2.5.1+cu121 and Unsloth have prebuilt binary wheels for Python 3.10 - 3.12.
    echo If installation fails, install Python 3.10 or 3.11, or use WSL2 (setup_env_wsl.sh).
)
echo.

:: 3. Create Dedicated Training Virtual Environment (venv-training)
echo [3/6] Configuring dedicated training virtual environment: venv-training...
if not exist "venv-training\Scripts\python.exe" (
    echo Creating venv-training...
    %PY_CMD% -m venv venv-training
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment venv-training!
        exit /b 1
    )
) else (
    echo Existing venv-training detected. Reusing environment.
)
echo.

:: 4. Upgrade pip and core packaging tools
echo [4/6] Upgrading pip, setuptools, and wheel...
.\venv-training\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
echo.

:: 5. Install PyTorch 2.5.1+cu121 (if not already installed)
echo [5/6] Validating / Installing PyTorch 2.5.1+cu121...
.\venv-training\Scripts\python.exe -c "import torch; assert '2.5.1' in torch.__version__ and 'cu121' in torch.__version__; print('PyTorch 2.5.1+cu121 already installed!')" >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing PyTorch 2.5.1+cu121 from official PyTorch repository...
    .\venv-training\Scripts\python.exe -m pip install torch==2.5.1+cu121 torchvision==0.20.1+cu121 torchaudio==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121
    if %errorlevel% neq 0 (
        echo [ERROR] PyTorch 2.5.1+cu121 installation failed.
        exit /b 1
    )
)
echo.

:: 6. Install Training Dependencies & Unsloth
echo [6/6] Installing fine-tuning packages (Transformers, TRL, PEFT, Datasets, Unsloth)...
.\venv-training\Scripts\python.exe -m pip install -r requirements-training.txt

echo.
echo ==============================================================================
echo  Verification & Diagnostics
echo ==============================================================================
.\venv-training\Scripts\python.exe -c "
import sys
try:
    import torch
    print('[OK] PyTorch Version:', torch.__version__)
    print('[OK] CUDA Available:', torch.cuda.is_available())
    if torch.cuda.is_available():
        print('[OK] Device Name:', torch.cuda.get_device_name(0))
        print('[OK] VRAM Total:', round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2), 'GB')
except Exception as e:
    print('[WARNING] PyTorch verification note:', e)

try:
    import transformers, trl, peft, datasets, unsloth
    print('[OK] Hugging Face & Unsloth packages successfully imported!')
except ImportError as e:
    print('[NOTE] Unsloth / dependencies notice on Windows:', e)
    print('If Triton or Unsloth encounters native Windows issues, run setup_env_wsl.sh under WSL2.')
"

echo.
echo Setup completed! To test the pipeline in dry-run mode, run:
echo   .\venv-training\Scripts\python.exe training\llm_trainer.py --dataset data\training\sample_rag_train.json --dry-run
echo ==============================================================================

