"""
Comprehensive Unit & Integration Test Suite for UniGuru LLM Training Pipeline.
Verifies dataset loading (JSON, JSONL, CSV), schema validation, prompt formatting,
hardware diagnostics, fallback computation, and dry-run execution on CPU.
"""
from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path
import pytest

from training.dataset_formatter import (
    RAG_PROMPT_TEMPLATE,
    format_dataset_for_sft,
    format_rag_inference_prompt,
    format_rag_record,
)
from training.dataset_loader import (
    DatasetValidationError,
    load_raw_dataset,
    split_dataset,
)
from training.llm_trainer import load_config, run_dry_run
from training.training_utils import (
    compute_batch_size_fallback,
    get_environment_info,
    validate_training_hardware,
)
from inference.llm_inference import RAGInferenceEngine


_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 1. Dataset Loader Tests (JSON, JSONL, CSV)
# ---------------------------------------------------------------------------

def test_load_sample_json_dataset():
    path = _ROOT / "data" / "training" / "sample_rag_train.json"
    records = load_raw_dataset(path)
    assert len(records) == 5
    for r in records:
        assert "context" in r and r["context"]
        assert "question" in r and r["question"]
        assert "answer" in r and r["answer"]


def test_load_sample_jsonl_dataset():
    path = _ROOT / "data" / "training" / "sample_rag_train.jsonl"
    records = load_raw_dataset(path)
    assert len(records) == 3
    for r in records:
        assert isinstance(r["context"], str) and len(r["context"]) > 0
        assert isinstance(r["question"], str) and len(r["question"]) > 0
        assert isinstance(r["answer"], str) and len(r["answer"]) > 0


def test_load_sample_csv_dataset():
    path = _ROOT / "data" / "training" / "sample_rag_train.csv"
    records = load_raw_dataset(path)
    assert len(records) == 3
    for r in records:
        assert "context" in r
        assert "question" in r
        assert "answer" in r


def test_missing_required_fields_raises_validation_error():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump([{"context": "some context", "question": "some question"}], f)  # missing 'answer'
        temp_path = Path(f.name)

    try:
        with pytest.raises(DatasetValidationError) as exc_info:
            load_raw_dataset(temp_path)
        assert "missing required fields" in str(exc_info.value).lower()
    finally:
        temp_path.unlink(missing_ok=True)


def test_empty_field_raises_validation_error():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump([{"context": "context", "question": "", "answer": "answer"}], f)
        temp_path = Path(f.name)

    try:
        with pytest.raises(DatasetValidationError) as exc_info:
            load_raw_dataset(temp_path)
        assert "'question' is empty" in str(exc_info.value)
    finally:
        temp_path.unlink(missing_ok=True)


def test_corrupt_json_raises_validation_error():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write("{ broken json ...")
        temp_path = Path(f.name)

    try:
        with pytest.raises(DatasetValidationError) as exc_info:
            load_raw_dataset(temp_path)
        assert "invalid json syntax" in str(exc_info.value).lower()
    finally:
        temp_path.unlink(missing_ok=True)


def test_dataset_split_no_leakage_and_deterministic():
    sample_records = [
        {"context": f"ctx {i}", "question": f"q {i}", "answer": f"a {i}"}
        for i in range(20)
    ]
    train1, val1 = split_dataset(sample_records, val_ratio=0.2, seed=42)
    train2, val2 = split_dataset(sample_records, val_ratio=0.2, seed=42)

    assert len(train1) == 16
    assert len(val1) == 4
    # Determinism check
    assert train1 == train2
    assert val1 == val2
    # Zero leakage check
    train_questions = {r["question"] for r in train1}
    val_questions = {r["question"] for r in val1}
    assert train_questions.isdisjoint(val_questions)


# ---------------------------------------------------------------------------
# 2. Prompt Formatter Tests
# ---------------------------------------------------------------------------

def test_rag_prompt_formatting():
    record = {
        "context": "Photosynthesis produces glucose and oxygen.",
        "question": "What does photosynthesis produce?",
        "answer": "Glucose and oxygen.",
    }
    formatted = format_rag_record(record, eos_token="<|im_end|>")
    assert "### System:" in formatted
    assert "You are a helpful assistant" in formatted
    assert "### Context:\nPhotosynthesis produces glucose and oxygen." in formatted
    assert "### Question:\nWhat does photosynthesis produce?" in formatted
    assert "### Answer:\nGlucose and oxygen.<|im_end|>" in formatted


def test_rag_inference_prompt_formatting():
    prompt = format_rag_inference_prompt(
        context="BHIV is a sovereign data system.",
        question="What is BHIV?",
    )
    assert "### Context:\nBHIV is a sovereign data system." in prompt
    assert "### Question:\nWhat is BHIV?" in prompt
    assert prompt.endswith("### Answer:\n")


def test_format_dataset_for_sft():
    records = [
        {"context": "C1", "question": "Q1", "answer": "A1"},
        {"context": "C2", "question": "Q2", "answer": "A2"},
    ]
    sft_records = format_dataset_for_sft(records)
    assert len(sft_records) == 2
    assert "text" in sft_records[0]
    assert "### Context:\nC1" in sft_records[0]["text"]
    assert "### Answer:\nA1" in sft_records[0]["text"]


# ---------------------------------------------------------------------------
# 3. Configuration & Hardware Utilities Tests
# ---------------------------------------------------------------------------

def test_load_training_yaml_configuration():
    config = load_config(_ROOT / "config" / "llm_training.yaml")
    assert config["model"]["name_or_path"] == "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"
    assert config["model"]["load_in_4bit"] is True
    assert config["model"]["max_seq_length"] == 2048

    # Verify mandatory QLoRA parameters
    qlora = config["qlora"]
    assert qlora["r"] == 16
    assert qlora["lora_alpha"] == 16
    assert qlora["lora_dropout"] == 0
    assert qlora["bias"] == "none"
    assert qlora["use_gradient_checkpointing"] == "unsloth"
    assert "q_proj" in qlora["target_modules"]
    assert "down_proj" in qlora["target_modules"]

    # Verify RTX 3060 hardware safety configs
    assert config["training"]["per_device_train_batch_size"] == 2
    assert config["training"]["gradient_accumulation_steps"] == 4
    assert config["hardware"]["fallback_batch_size"] == 1


def test_environment_info_detection():
    info = get_environment_info()
    assert "python_version" in info
    assert "torch_available" in info
    assert "cuda_available" in info
    assert isinstance(info["devices"], list)


def test_hardware_validation_cpu_mock_mode():
    hw = validate_training_hardware(min_vram_gb=10.5, allow_cpu_mock=True)
    assert hw["device"] in ("cpu", "cuda:0")
    assert "name" in hw
    assert "supports_bf16" in hw
    assert "supports_fp16" in hw


def test_batch_size_fallback_calculation():
    new_bs, new_accum = compute_batch_size_fallback(
        base_batch_size=2,
        base_grad_accum=4,
        fallback_batch_size=1,
    )
    assert new_bs == 1
    assert new_accum == 8
    # Effective batch size preserved: 2 * 4 == 1 * 8 == 8


# ---------------------------------------------------------------------------
# 4. Pipeline Dry-Run Workflow Test (CPU Friendly)
# ---------------------------------------------------------------------------

def test_pipeline_dry_run_execution():
    config = load_config(_ROOT / "config" / "llm_training.yaml")
    train_path = _ROOT / "data" / "training" / "sample_rag_train.json"
    val_path = _ROOT / "data" / "validation" / "sample_rag_val.json"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_output = Path(tmp_dir) / "checkpoints"
        tmp_adapter = Path(tmp_dir) / "adapter"

        # Must execute cleanly without exceptions
        run_dry_run(
            config=config,
            dataset_path=train_path,
            val_dataset_path=val_path,
            output_dir=tmp_output,
            adapter_dir=tmp_adapter,
        )

        assert tmp_output.is_dir()
        assert tmp_adapter.is_dir()


# ---------------------------------------------------------------------------
# 5. Inference Engine Instantiation Test
# ---------------------------------------------------------------------------

def test_inference_engine_initialization():
    engine = RAGInferenceEngine(
        adapter_path=_ROOT / "models" / "adapters" / "qwen2.5-7b-rag-adapter",
        config_path=_ROOT / "config" / "llm_training.yaml",
    )
    assert engine.loaded is False
    assert engine.base_model_name == "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"
    
    # Empty context/question validation without model loading
    assert "I do not know" in engine.generate(context="", question="What is X?")
    assert "valid question" in engine.generate(context="Some context", question="")

