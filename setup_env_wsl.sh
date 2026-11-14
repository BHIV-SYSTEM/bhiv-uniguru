#!/usr/bin/env bash
# ==============================================================================
# UniGuru Qwen 2.5 7B QLoRA Fine-Tuning Setup for WSL2 / Linux
# Target Hardware: NVIDIA GeForce RTX 3060 (12GB VRAM)
# Target Stack: Python 3.10 - 3.12 | PyTorch 2.5.1+cu121 | CUDA 12.1 | Unsloth
# Recommended for maximum stability with Triton & BitsAndBytes
# ==============================================================================
set -euo pipefail

echo "=============================================================================="
echo " UniGuru LLM Training Environment Setup (WSL2 / Linux)"
echo "=============================================================================="

# 1. Check NVIDIA GPU pass-through
echo "[1/6] Checking NVIDIA GPU and driver access in WSL2..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
else
    echo "[WARNING] 'nvidia-smi' not found in WSL2."
    echo "Make sure the latest NVIDIA Driver is installed on Windows host and WSL2 GPU pass-through is active."
fi

# 2. Check Python installation
echo "[2/6] Checking Python installation..."
PYTHON_BIN=""
for candidate in python3.11 python3.10 python3.12 python3; do
    if command -v "$candidate" &> /dev/null; then
        PYTHON_BIN="$candidate"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "[ERROR] Python 3 was not found! Please run: sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
    exit 1
fi

echo "Using Python binary: $PYTHON_BIN ($($PYTHON_BIN --version))"

# 3. Create isolated virtual environment
echo "[3/6] Setting up venv-training..."
if [ ! -f "venv-training/bin/python" ]; then
    "$PYTHON_BIN" -m venv venv-training
fi
source venv-training/bin/activate

# 4. Upgrade pip and build tools
echo "[4/6] Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# 5. Install PyTorch 2.5.1+cu121
echo "[5/6] Installing / Validating PyTorch 2.5.1+cu121..."
python -c "import torch; assert '2.5.1' in torch.__version__ and 'cu121' in torch.__version__" 2>/dev/null || {
    pip install torch==2.5.1+cu121 torchvision==0.20.1+cu121 torchaudio==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121
}

# 6. Install fine-tuning dependencies and Unsloth
echo "[6/6] Installing Unsloth, TRL, Transformers, and training dependencies..."
pip install "unsloth[cu121-torch250] @ git+https://github.com/unslothai/unsloth.git" || pip install unsloth
pip install -r requirements-training.txt

echo "=============================================================================="
echo " Validation & Diagnostics"
echo "=============================================================================="
python -c "
import torch
print('[OK] PyTorch Version:', torch.__version__)
print('[OK] CUDA Available:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('[OK] Device Name:', torch.cuda.get_device_name(0))
    print('[OK] VRAM:', round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2), 'GB')

import transformers, trl, peft, datasets, unsloth
print('[OK] All training libraries imported successfully!')
"

echo "=============================================================================="
echo " Setup complete! To run a dry-run test:"
echo "   python training/llm_trainer.py --dataset data/training/sample_rag_train.json --dry-run"
echo "=============================================================================="

