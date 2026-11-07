"""
UniGuru Qwen 2.5 7B QLoRA Fine-Tuning Pipeline.
Model: unsloth/Qwen2.5-7B-Instruct-bnb-4bit
Target Hardware: NVIDIA GeForce RTX 3060 (12GB VRAM)
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from training.dataset_formatter import format_dataset_for_sft, format_rag_record
from training.dataset_loader import DatasetValidationError, load_raw_dataset, split_dataset
from training.training_utils import (
    HardwareCompatibilityError,
    VRAMExhaustionError,
    compute_batch_size_fallback,
    get_environment_info,
    release_cuda_memory,
    save_training_metadata,
    validate_training_hardware,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("uniguru.training.trainer")


def load_config(config_path: Optional[str | Path] = None) -> Dict[str, Any]:
    """Load configuration from YAML file with default fallbacks."""
    default_path = _PROJECT_ROOT / "config" / "llm_training.yaml"
    path = Path(config_path) if config_path else default_path

    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path.resolve()}")

    with path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg or {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="UniGuru Qwen 2.5 7B QLoRA Fine-Tuning Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=str,
        default=str(_PROJECT_ROOT / "config" / "llm_training.yaml"),
        help="Path to training YAML configuration file",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Path to training dataset (.json, .jsonl, .csv)",
    )
    parser.add_argument(
        "--val-dataset",
        type=str,
        default=None,
        help="Optional path to validation dataset (.json, .jsonl, .csv)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save training checkpoints",
    )
    parser.add_argument(
        "--adapter-dir",
        type=str,
        default=None,
        help="Directory to save the final fine-tuned LoRA adapter",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=None,
        help="Number of training epochs (overrides config)",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=None,
        help="Learning rate (overrides config)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Per-device train batch size (overrides config)",
    )
    parser.add_argument(
        "--max-seq-length",
        type=int,
        default=None,
        help="Maximum sequence length (overrides config)",
    )
    parser.add_argument(
        "--resume-from-checkpoint",
        type=str,
        default=None,
        help="Path to checkpoint folder to resume training from",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate hardware, dependencies, dataset schema, and training config without downloading weights or training",
    )
    return parser.parse_args()


def run_dry_run(
    config: Dict[str, Any],
    dataset_path: Path,
    val_dataset_path: Optional[Path],
    output_dir: Path,
    adapter_dir: Path,
) -> None:
    """Execute non-destructive dry-run validation on any machine (CPU or GPU)."""
    logger.info("==================================================================")
    logger.info(" [DRY-RUN] UniGuru Qwen 2.5 Fine-Tuning Pipeline Validation")
    logger.info("==================================================================")

    # 1. Environment & Hardware Check
    env = get_environment_info()
    logger.info(f"Python Runtime: {sys.version.split()[0]} on {sys.platform}")
    logger.info(f"PyTorch Available: {env['torch_available']} (version: {env['torch_version']})")
    logger.info(f"CUDA Available: {env['cuda_available']} (driver CUDA: {env['cuda_version']})")
    
    hw = validate_training_hardware(allow_cpu_mock=True)
    logger.info(f"Active Execution Device: {hw['device']} ({hw['name']})")
    logger.info(f"Total VRAM Reported: {hw['total_memory_gb']} GB")
    logger.info(f"BF16 Supported: {hw['supports_bf16']} | FP16 Supported: {hw['supports_fp16']}")

    # 2. Dataset Loading & Schema Validation
    logger.info(f"Loading training dataset: {dataset_path}")
    train_records = load_raw_dataset(dataset_path)
    logger.info(f" Successfully loaded and validated {len(train_records)} training records.")

    if val_dataset_path and val_dataset_path.is_file():
        logger.info(f"Loading validation dataset: {val_dataset_path}")
        val_records = load_raw_dataset(val_dataset_path)
        logger.info(f" Successfully loaded and validated {len(val_records)} validation records.")
    else:
        split_ratio = float(config.get("dataset", {}).get("validation_split", 0.1))
        train_split, val_split = split_dataset(train_records, val_ratio=split_ratio)
        logger.info(
            f" Split dataset: {len(train_split)} train records, {len(val_split)} validation records (ratio: {split_ratio})."
        )

    # 3. Prompt Formatting & Token Inspection
    logger.info("Inspecting formatted RAG training prompt sample:")
    sample_prompt = format_rag_record(train_records[0], eos_token="<|im_end|>")
    print("\n--- SAMPLE FORMATTED PROMPT ---")
    print(sample_prompt[:400] + ("\n... [truncated]" if len(sample_prompt) > 400 else ""))
    print("--------------------------------\n")

    # 4. Directory Verification
    output_dir.mkdir(parents=True, exist_ok=True)
    adapter_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f" Checkpoints destination verified: {output_dir.resolve()}")
    logger.info(f" Adapter destination verified: {adapter_dir.resolve()}")

    # 5. Configuration Summary
    model_cfg = config.get("model", {})
    qlora_cfg = config.get("qlora", {})
    train_cfg = config.get("training", {})
    logger.info(f"Target Model: {model_cfg.get('name_or_path')}")
    logger.info(f"4-bit Loading: {model_cfg.get('load_in_4bit')}")
    logger.info(f"LoRA Rank (r): {qlora_cfg.get('r')} | Alpha: {qlora_cfg.get('lora_alpha')}")
    logger.info(f"Target Projections: {qlora_cfg.get('target_modules')}")
    logger.info(f"Batch Size: {train_cfg.get('per_device_train_batch_size')} (Grad Accum: {train_cfg.get('gradient_accumulation_steps')})")
    logger.info(f"Optimizer: {train_cfg.get('optim')}")

    logger.info("==================================================================")
    logger.info(" [DRY-RUN SUCCESS] Pipeline configuration and datasets are 100% VALID.")
    logger.info(" Ready for execution on NVIDIA RTX 3060 (12GB) machine.")
    logger.info("==================================================================")


def train_model(
    config: Dict[str, Any],
    dataset_path: Path,
    val_dataset_path: Optional[Path],
    output_dir: Path,
    adapter_dir: Path,
    resume_from_checkpoint: Optional[str] = None,
) -> None:
    """
    Execute 4-bit QLoRA fine-tuning using Unsloth and Hugging Face TRL SFTTrainer.
    Strictly executed only on a compatible NVIDIA GPU (RTX 3060 12GB+).
    """
    logger.info("Starting UniGuru Qwen 2.5 7B QLoRA Fine-Tuning Pipeline...")

    # Step 1: Strict Hardware Validation
    min_vram = float(config.get("hardware", {}).get("min_required_vram_gb", 10.5))
    hw = validate_training_hardware(min_vram_gb=min_vram, allow_cpu_mock=False)
    logger.info(f"Verified GPU: {hw['name']} with {hw['total_memory_gb']} GB VRAM.")

    # Step 2: Load and validate datasets
    train_raw = load_raw_dataset(dataset_path)
    if val_dataset_path and val_dataset_path.is_file():
        val_raw = load_raw_dataset(val_dataset_path)
    else:
        split_ratio = float(config.get("dataset", {}).get("validation_split", 0.1))
        train_raw, val_raw = split_dataset(train_raw, val_ratio=split_ratio)

    logger.info(f"Dataset prepared: {len(train_raw)} train samples, {len(val_raw)} validation samples.")

    # Step 3: Import Unsloth & Transformers
    try:
        from unsloth import FastLanguageModel
        from trl import SFTTrainer
        from transformers import TrainingArguments
        from datasets import Dataset
    except ImportError as exc:
        raise HardwareCompatibilityError(
            f"Required training frameworks are missing ({exc}). "
            "Please run `setup_env.bat` or `setup_env_wsl.sh` on the training machine."
        ) from exc

    # Step 4: Load Base Model in 4-bit
    model_cfg = config.get("model", {})
    max_seq_length = int(model_cfg.get("max_seq_length", 2048))
    dtype = None  # None = auto-detect float16/bfloat16
    load_in_4bit = bool(model_cfg.get("load_in_4bit", True))
    model_name = str(model_cfg.get("name_or_path", "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"))

    logger.info(f"Loading {model_name} in 4-bit mode (max_seq_length={max_seq_length})...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        dtype=dtype,
        load_in_4bit=load_in_4bit,
    )

    # Step 5: Configure LoRA Adapter
    qlora_cfg = config.get("qlora", {})
    r = int(qlora_cfg.get("r", 16))
    lora_alpha = int(qlora_cfg.get("lora_alpha", 16))
    lora_dropout = float(qlora_cfg.get("lora_dropout", 0))
    target_modules = list(qlora_cfg.get("target_modules", [
        "q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"
    ]))
    use_gradient_checkpointing = qlora_cfg.get("use_gradient_checkpointing", "unsloth")
    random_state = int(qlora_cfg.get("random_state", 3407))

    logger.info(f"Applying QLoRA adapter (rank={r}, alpha={lora_alpha}, target_modules={target_modules})...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=r,
        target_modules=target_modules,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        bias="none",
        use_gradient_checkpointing=use_gradient_checkpointing,
        random_state=random_state,
        max_seq_length=max_seq_length,
    )

    # Step 6: Format Hugging Face Datasets
    eos_token = tokenizer.eos_token or "<|im_end|>"
    train_formatted = format_dataset_for_sft(train_raw, eos_token=eos_token)
    val_formatted = format_dataset_for_sft(val_raw, eos_token=eos_token) if val_raw else None

    train_dataset = Dataset.from_list(train_formatted)
    eval_dataset = Dataset.from_list(val_formatted) if val_formatted else None

    # Step 7: Configure Training Arguments with VRAM Safety
    train_cfg = config.get("training", {})
    batch_size = int(train_cfg.get("per_device_train_batch_size", 2))
    grad_accum = int(train_cfg.get("gradient_accumulation_steps", 4))
    lr = float(train_cfg.get("learning_rate", 2e-4))
    epochs = int(train_cfg.get("num_train_epochs", 3))
    optim = str(train_cfg.get("optim", "adamw_8bit"))
    save_limit = int(train_cfg.get("save_total_limit", 2))

    use_bf16 = hw["supports_bf16"]
    use_fp16 = not use_bf16 and hw["supports_fp16"]

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        learning_rate=lr,
        num_train_epochs=epochs,
        fp16=use_fp16,
        bf16=use_bf16,
        logging_steps=int(train_cfg.get("logging_steps", 1)),
        optim=optim,
        weight_decay=float(train_cfg.get("weight_decay", 0.01)),
        lr_scheduler_type=str(train_cfg.get("lr_scheduler_type", "linear")),
        seed=random_state,
        save_strategy=str(train_cfg.get("save_strategy", "epoch")),
        save_total_limit=save_limit,
        report_to="none",
    )

    # Step 8: Initialize SFTTrainer
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        dataset_num_proc=int(train_cfg.get("dataset_num_proc", 2)),
        packing=bool(train_cfg.get("packing", False)),
        args=training_args,
    )

    # Step 9: Execute Fine-Tuning with OOM Recovery
    logger.info("Beginning fine-tuning...")
    t0 = time.time()
    try:
        trainer_stats = trainer.train(resume_from_checkpoint=resume_from_checkpoint)
        training_time = time.time() - t0
        logger.info(f"Training completed successfully in {training_time:.2f} seconds!")
    except torch.cuda.OutOfMemoryError as oom_exc:
        logger.error(f"[CUDA OOM] Training ran out of memory: {oom_exc}")
        release_cuda_memory()
        fallback_bs, fallback_ga = compute_batch_size_fallback(batch_size, grad_accum)
        logger.warning(
            f"Restart training using: python training/llm_trainer.py --batch-size {fallback_bs}"
        )
        raise

    # Step 10: Save Final LoRA Adapter
    adapter_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Saving fine-tuned LoRA adapter to {adapter_dir}...")
    model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))

    # Save run metadata
    metadata = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "base_model": model_name,
        "max_seq_length": max_seq_length,
        "lora_rank": r,
        "lora_alpha": lora_alpha,
        "epochs": epochs,
        "batch_size": batch_size,
        "gradient_accumulation_steps": grad_accum,
        "learning_rate": lr,
        "training_time_seconds": round(training_time, 2),
        "hardware": hw,
        "training_samples": len(train_raw),
        "validation_samples": len(val_raw) if val_raw else 0,
    }
    save_training_metadata(adapter_dir, metadata)
    logger.info(f" Adapter and run metadata saved successfully in {adapter_dir}.")


def main() -> None:
    args = parse_args()
    config = load_config(args.config)

    # Resolve paths (CLI overrides > Config > Defaults)
    dataset_str = args.dataset or config.get("dataset", {}).get("train_path", "data/training/sample_rag_train.json")
    dataset_path = Path(dataset_str)
    if not dataset_path.is_absolute():
        dataset_path = _PROJECT_ROOT / dataset_path

    val_dataset_str = args.val_dataset or config.get("dataset", {}).get("validation_path")
    val_dataset_path = None
    if val_dataset_str:
        p = Path(val_dataset_str)
        val_dataset_path = p if p.is_absolute() else _PROJECT_ROOT / p

    output_dir_str = args.output_dir or config.get("paths", {}).get("checkpoints_dir", "checkpoints")
    output_dir = Path(output_dir_str)
    if not output_dir.is_absolute():
        output_dir = _PROJECT_ROOT / output_dir

    adapter_dir_str = args.adapter_dir or config.get("paths", {}).get("adapter_dir", "models/adapters/qwen2.5-7b-rag-adapter")
    adapter_dir = Path(adapter_dir_str)
    if not adapter_dir.is_absolute():
        adapter_dir = _PROJECT_ROOT / adapter_dir

    # Apply CLI parameter overrides to config
    if args.epochs is not None:
        config.setdefault("training", {})["num_train_epochs"] = args.epochs
    if args.learning_rate is not None:
        config.setdefault("training", {})["learning_rate"] = args.learning_rate
    if args.batch_size is not None:
        config.setdefault("training", {})["per_device_train_batch_size"] = args.batch_size
    if args.max_seq_length is not None:
        config.setdefault("model", {})["max_seq_length"] = args.max_seq_length

    if args.dry_run:
        run_dry_run(
            config=config,
            dataset_path=dataset_path,
            val_dataset_path=val_dataset_path,
            output_dir=output_dir,
            adapter_dir=adapter_dir,
        )
    else:
        train_model(
            config=config,
            dataset_path=dataset_path,
            val_dataset_path=val_dataset_path,
            output_dir=output_dir,
            adapter_dir=adapter_dir,
            resume_from_checkpoint=args.resume_from_checkpoint,
        )


if __name__ == "__main__":
    main()

