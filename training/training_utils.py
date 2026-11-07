"""
Hardware Diagnostics, VRAM Safety, and Resource Management for UniGuru Fine-Tuning.
Target Hardware: NVIDIA GeForce RTX 3060 (12GB VRAM).
"""
from __future__ import annotations

import gc
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("uniguru.training.utils")


class HardwareCompatibilityError(RuntimeError):
    """Raised when the host environment does not meet the minimum hardware requirements."""
    pass


class VRAMExhaustionError(RuntimeError):
    """Raised when available GPU memory is insufficient for 7B QLoRA fine-tuning."""
    pass


def get_environment_info() -> Dict[str, Any]:
    """Inspect and return current Python, OS, PyTorch, and CUDA environment metadata."""
    info: Dict[str, Any] = {
        "python_version": sys.version,
        "platform": sys.platform,
        "torch_available": False,
        "torch_version": None,
        "cuda_available": False,
        "cuda_version": None,
        "device_count": 0,
        "devices": [],
    }

    try:
        import torch
        info["torch_available"] = True
        info["torch_version"] = torch.__version__
        info["cuda_available"] = torch.cuda.is_available()
        info["cuda_version"] = torch.version.cuda
        if torch.cuda.is_available():
            info["device_count"] = torch.cuda.device_count()
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                total_mem_gb = round(props.total_memory / (1024 ** 3), 2)
                info["devices"].append({
                    "index": i,
                    "name": props.name,
                    "major": props.major,
                    "minor": props.minor,
                    "compute_capability": f"{props.major}.{props.minor}",
                    "total_memory_gb": total_mem_gb,
                })
    except ImportError:
        pass

    return info


def validate_training_hardware(
    min_vram_gb: float = 10.5,
    allow_cpu_mock: bool = False,
) -> Dict[str, Any]:
    """
    Validate that a compatible NVIDIA GPU with sufficient VRAM is available.
    Returns hardware specs dictionary.
    Raises HardwareCompatibilityError if requirements are not met and allow_cpu_mock is False.
    """
    env = get_environment_info()

    if not env["torch_available"]:
        raise HardwareCompatibilityError("PyTorch is not installed in the active environment.")

    if not env["cuda_available"]:
        if allow_cpu_mock:
            logger.warning("[DRY-RUN] No CUDA GPU detected. Proceeding in CPU mock mode.")
            return {
                "device": "cpu",
                "name": "CPU (Mock Mode)",
                "compute_capability": "0.0",
                "total_memory_gb": 0.0,
                "supports_bf16": False,
                "supports_fp16": False,
                "recommended_dtype": "float32",
            }
        raise HardwareCompatibilityError(
            "CUDA is not available. 4-bit QLoRA fine-tuning requires an NVIDIA GPU with CUDA 12.1+."
        )

    import torch
    device_idx = 0
    props = torch.cuda.get_device_properties(device_idx)
    total_mem_gb = props.total_memory / (1024 ** 3)
    major, minor = props.major, props.minor

    logger.info(
        f"Detected GPU: {props.name} | Compute Capability: {major}.{minor} | VRAM: {total_mem_gb:.2f} GB"
    )

    if total_mem_gb < min_vram_gb:
        if allow_cpu_mock:
            logger.warning(
                f"[DRY-RUN] GPU VRAM ({total_mem_gb:.2f} GB) is below recommended ({min_vram_gb:.2f} GB). "
                "Allowed for dry-run validation."
            )
        else:
            raise VRAMExhaustionError(
                f"GPU VRAM ({total_mem_gb:.2f} GB) is below the required {min_vram_gb} GB for 7B QLoRA. "
                "Target machine must be an RTX 3060 (12GB) or higher."
            )

    # Ampere (RTX 3060 is CC 8.6), Ada, and Hopper support BF16 natively
    supports_bf16 = (major >= 8) and hasattr(torch.cuda, "is_bf16_supported") and torch.cuda.is_bf16_supported()
    supports_fp16 = major >= 7

    recommended_dtype = "bfloat16" if supports_bf16 else ("float16" if supports_fp16 else "float32")

    return {
        "device": "cuda:0",
        "name": props.name,
        "compute_capability": f"{major}.{minor}",
        "total_memory_gb": round(total_mem_gb, 2),
        "supports_bf16": supports_bf16,
        "supports_fp16": supports_fp16,
        "recommended_dtype": recommended_dtype,
    }


def compute_batch_size_fallback(
    base_batch_size: int,
    base_grad_accum: int,
    fallback_batch_size: int = 1,
) -> Tuple[int, int]:
    """
    Adjust batch size and gradient accumulation to preserve effective batch size
    while cutting peak VRAM consumption during OOM recovery.
    Effective Batch Size = per_device_batch_size * gradient_accumulation_steps
    """
    effective = base_batch_size * base_grad_accum
    new_accum = max(1, effective // fallback_batch_size)
    logger.warning(
        f"[VRAM RECOVERY] Fallback applied: batch_size {base_batch_size}->{fallback_batch_size}, "
        f"gradient_accumulation {base_grad_accum}->{new_accum} (Effective batch size: {effective})"
    )
    return fallback_batch_size, new_accum


def release_cuda_memory() -> None:
    """Trigger Python garbage collection and release cached CUDA allocations."""
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception:
        pass


def save_training_metadata(
    output_dir: str | Path,
    metadata: Dict[str, Any],
) -> Path:
    """Save training parameters, commit hash, and hardware info to output directory."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    meta_path = out / "training_run_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return meta_path

