# UniGuru Qwen 2.5 7B QLoRA Fine-Tuning Guide

This guide provides complete, step-by-step instructions to set up, fine-tune, save, and evaluate **Qwen 2.5 7B Instruct** using **4-bit QLoRA** and **Unsloth** on an **NVIDIA GeForce RTX 3060 (12GB VRAM)** machine, while keeping your existing development machine and production services completely safe.

---

## 1. Overall Architecture

The fine-tuning pipeline is designed to be fully modular, isolated, and parameter-efficient:

```
Pretrained Qwen 2.5 7B Instruct (unsloth/Qwen2.5-7B-Instruct-bnb-4bit)
                       │
                       ▼
          4-bit BitsAndBytes Quantization
                       │
                       ▼
          Unsloth FastLanguageModel Engine
                       │
                       ▼
          LoRA Adapter Injection (r=16, alpha=16)
                       │
                       ▼
     Local Dataset Loading (JSON / JSONL / CSV)
                       │
                       ▼
           RAG Prompt Format Transformation
                       │
                       ▼
        Hugging Face TRL SFTTrainer Execution
                       │
                       ▼
         LoRA Adapter Checkpoint (models/adapters/)
                       │
                       ▼
    RAG Grounded Inference Engine (inference/llm_inference.py)
```

---

## 2. Model Selection & Licensing

- **Base Checkpoint**: `unsloth/Qwen2.5-7B-Instruct-bnb-4bit`
- **Parameter Count**: 7.61 Billion parameters
- **Quantization**: 4-bit NormalFloat (NF4) via `bitsandbytes`
- **Context Length**: Up to 2,048 tokens (configurable up to 32k on higher VRAM)
- **License**: **Apache 2.0 / Qwen Community License** (Commercial and research friendly)
- **Suitability**: Specifically tuned for instruction following, multi-turn reasoning, structured JSON generation, and strict grounded RAG question answering.

> [!IMPORTANT]
> Model weights are **never downloaded automatically** during setup. Weights are only fetched when you explicitly initiate training or inference on a compatible GPU machine.

---

## 3. Hardware Requirements

| Component | Training Machine Requirement | Development Machine Behavior |
| :--- | :--- | :--- |
| **GPU** | NVIDIA GeForce RTX 3060 (or higher) | Any (or integrated / legacy GPU) |
| **VRAM** | **12 GB VRAM minimum** | 2 GB or CPU-only |
| **CUDA Driver** | CUDA 12.1+ (NVIDIA Driver >= 530.xx) | None required for validation |
| **RAM** | 16 GB+ System RAM | 8 GB+ System RAM |
| **Disk Space** | ~15 GB free for base model + checkpoints | < 100 MB for scripts & config |
| **Execution** | Full 4-bit QLoRA SFT Training | `--dry-run` and dataset validation only |

---

## 4. Operating System Compatibility: Native Windows vs. WSL2

### Why WSL2 / Linux is Strongly Recommended
Unsloth utilizes **OpenAI Triton** for fused kernel acceleration (RoPE scaling, cross-entropy loss, and 4-bit GEMM).
- **WSL2 / Linux (Ubuntu 22.04 or 24.04)**: Triton and PyTorch 2.5.1+cu121 are natively supported with 100% stability and zero compilation overhead.
- **Native Windows**: While modern Unsloth includes experimental Windows support via `triton-windows`, Windows path limits, MSVC build tool requirements, and asynchronous CUDA IPC issues can cause sporadic training halts.

**Recommendation**: When moving to the RTX 3060 machine, run the setup inside **WSL2** (`setup_env_wsl.sh`) for optimal speed and reliability. If native Windows is your only option, use `setup_env.bat`.

---

## 5. Environment Installation

### Option A: WSL2 / Linux (Recommended)

1. Open your WSL2 terminal (e.g. Ubuntu 22.04) and navigate to the project repository:
   ```bash
   cd /mnt/c/blackhole159_SV/BHIV_UNIGURU
   ```
2. Make the script executable and run it:
   ```bash
   chmod +x setup_env_wsl.sh
   ./setup_env_wsl.sh
   ```
3. Activate the dedicated training virtual environment:
   ```bash
   source venv-training/bin/activate
   ```

### Option B: Native Windows (PowerShell / CMD)

1. Open PowerShell or Command Prompt in the repository root:
   ```powershell
   cd c:\blackhole159_SV\BHIV_UNIGURU
   ```
2. Execute the Windows environment setup:
   ```cmd
   setup_env.bat
   ```
3. Activate the environment:
   ```powershell
   .\venv-training\Scripts\Activate.ps1
   ```

---

## 6. Dataset Preparation & Format Examples

The pipeline accepts datasets in **JSON**, **JSONL**, or **CSV** format. Source files must contain the three canonical fields: `context`, `question`, and `answer`.

### Format 1: JSON (`data/training/train.json`)
```json
[
  {
    "context": "Photosynthesis is the process by which green plants convert sunlight and carbon dioxide into oxygen and glucose.",
    "question": "What is photosynthesis?",
    "answer": "Photosynthesis is the process by which green plants convert sunlight and carbon dioxide into oxygen and glucose."
  }
]
```

### Format 2: JSONL (`data/training/train.jsonl`)
```json
{"context": "Newton's second law states that F = ma.", "question": "What is Newton's second law?", "answer": "Newton's second law states that force equals mass times acceleration (F = ma)."}
```

### Format 3: CSV (`data/training/train.csv`)
```csv
context,question,answer
"Drip irrigation delivers water directly to plant roots.","What is drip irrigation?","Drip irrigation delivers water directly to plant roots."
```

### Canonical RAG Prompt Template Applied During Training
```text
### System:
You are a helpful assistant. You must answer the user's question using ONLY the provided text context. If the answer is not in the context, say "I do not know".

### Context:
{context}

### Question:
{question}

### Answer:
{answer}
```

---

## 7. How to Start Training

### Step 1: Validate Setup with a Dry-Run
Before starting actual training, run the pipeline with `--dry-run` to verify dataset integrity, schema validation, and prompt formatting without downloading weights:
```powershell
python training/llm_trainer.py --dataset data/training/sample_rag_train.json --dry-run
```

### Step 2: Launch Actual 4-bit QLoRA Fine-Tuning
On the RTX 3060 machine with GPU access, run:
```powershell
python training/llm_trainer.py --dataset data/training/train.json
```

### Useful Command-Line Flags
- `--dataset <path>`: Path to training file (`.json`, `.jsonl`, `.csv`).
- `--val-dataset <path>`: Optional separate validation file.
- `--epochs <int>`: Number of training epochs (e.g. `--epochs 3`).
- `--learning-rate <float>`: Learning rate override (e.g. `--learning-rate 0.0002`).
- `--batch-size <int>`: Batch size override (e.g. `--batch-size 1` for tight VRAM).
- `--max-seq-length <int>`: Maximum sequence length (e.g. `--max-seq-length 1024`).
- `--output-dir <path>`: Directory for intermediate checkpoints.
- `--adapter-dir <path>`: Final destination for the trained LoRA adapter.
- `--resume-from-checkpoint <path>`: Resume an interrupted training session.

---

## 8. Resuming an Interrupted Training Session

If training was interrupted (power loss or manual cancel), you can resume seamlessly from the latest saved checkpoint:

```powershell
python training/llm_trainer.py \
  --dataset data/training/train.json \
  --resume-from-checkpoint checkpoints/checkpoint-100
```

---

## 9. Where Adapters and Checkpoints Are Stored

- **Final LoRA Adapter**:
  ```text
  models/adapters/qwen2.5-7b-rag-adapter/
  ├── adapter_config.json
  ├── adapter_model.safetensors
  ├── special_tokens_map.json
  ├── tokenizer_config.json
  ├── vocab.json / merges.txt
  └── training_run_metadata.json
  ```
- **Intermediate Checkpoints**: Stored under `checkpoints/checkpoint-<step>/` (automatically managed with `save_total_limit: 2`).

> [!NOTE]
> All model weights, adapters, and checkpoints are **excluded from Git tracking** in `.gitignore` to prevent repository bloat.

---

## 10. How to Run Inference with the Fine-Tuned Model

Once the adapter is trained and saved, launch the inference engine:

### Single Query Mode
```powershell
python inference/llm_inference.py \
  --context "Drip irrigation reduces water evaporation and runoff by up to 60%." \
  --question "How much water does drip irrigation save?"
```

### Interactive Console Mode
```powershell
python inference/llm_inference.py --interactive
```

---

## 11. CUDA Out-of-Memory (OOM) Fixes for RTX 3060 (12GB)

The RTX 3060 has 12GB of VRAM. If you encounter `torch.cuda.OutOfMemoryError`:

1. **Reduce Batch Size to 1**:
   ```powershell
   python training/llm_trainer.py --batch-size 1
   ```
   *(The pipeline will automatically adjust gradient accumulation to 8 to preserve the effective batch size of 8).*
2. **Shorten Maximum Sequence Length**:
   If your training documents are short, set `--max-seq-length 1024`:
   ```powershell
   python training/llm_trainer.py --max-seq-length 1024 --batch-size 1
   ```
3. **Close Background GPU Applications**:
   Ensure web browsers with hardware acceleration or gaming overlays are closed before training.

---

## 12. Transferring the Project to Another GPU Machine

To copy or clone this project onto your RTX 3060 machine:

1. Clone or copy the repository folder:
   ```bash
   git clone <repo-url>
   cd BHIV_UNIGURU
   ```
2. Run the setup script:
   - On WSL2 (recommended): `./setup_env_wsl.sh`
   - On Windows: `setup_env.bat`
3. Copy your local training dataset into `data/training/train.json`.
4. Run the dry-run test:
   ```bash
   python training/llm_trainer.py --dataset data/training/train.json --dry-run
   ```
5. Start training:
   ```bash
   python training/llm_trainer.py --dataset data/training/train.json
   ```

---

## 13. Component Breakdown: Mandatory vs. Optional

| Component | Status | Description |
| :--- | :---: | :--- |
| `config/llm_training.yaml` | **Mandatory** | Centralized parameter configuration |
| `training/dataset_loader.py` | **Mandatory** | Schema normalization for JSON, JSONL, and CSV |
| `training/dataset_formatter.py`| **Mandatory** | Canonical RAG prompt formatting |
| `training/training_utils.py` | **Mandatory** | VRAM check, BF16/FP16 detection, fallback |
| `training/llm_trainer.py` | **Mandatory** | SFTTrainer entry point |
| `inference/llm_inference.py` | **Mandatory** | 4-bit LoRA inference pipeline |
| `requirements-training.txt` | **Mandatory** | Pinned dependencies for PyTorch 2.5.1+cu121 & Unsloth |
| `setup_env_wsl.sh` | **Recommended**| One-click environment setup for WSL2 |
| `setup_env.bat` | Optional | Native Windows setup script |
| `data/training/sample_*` | Optional | Synthetic test fixtures for pipeline validation |

