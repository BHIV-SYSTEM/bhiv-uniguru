"""
Dataset Loader & Normalizer for UniGuru RAG LLM Fine-Tuning.
Supports JSON, JSONL, and CSV input formats with strict schema validation.
"""
from __future__ import annotations

import csv
import json
import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("uniguru.training.dataset_loader")

REQUIRED_FIELDS = ("context", "question", "answer")


class DatasetValidationError(ValueError):
    """Raised when an input training dataset violates schema or content constraints."""
    pass


def load_raw_dataset(file_path: str | Path) -> List[Dict[str, str]]:
    """
    Load and normalize records from a JSON, JSONL, or CSV file.
    Each returned item is guaranteed to be a dict with 'context', 'question', 'answer'.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset file does not exist: {path.resolve()}")

    suffix = path.suffix.lower()
    if suffix == ".json":
        return _load_json(path)
    elif suffix in (".jsonl", ".ndjson"):
        return _load_jsonl(path)
    elif suffix == ".csv":
        return _load_csv(path)
    else:
        raise DatasetValidationError(
            f"Unsupported file format '{suffix}' for {path.name}. Supported: .json, .jsonl, .csv"
        )


def _load_json(path: Path) -> List[Dict[str, str]]:
    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise DatasetValidationError(f"Invalid JSON syntax in {path.name}: {exc}") from exc

    if not isinstance(data, list):
        raise DatasetValidationError(
            f"JSON dataset must be a list of objects, got {type(data).__name__} in {path.name}"
        )
    return _validate_and_normalize_records(data, source_name=path.name)


def _load_jsonl(path: Path) -> List[Dict[str, str]]:
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                item = json.loads(line_str)
            except json.JSONDecodeError as exc:
                raise DatasetValidationError(
                    f"Invalid JSON on line {line_num} of {path.name}: {exc}"
                ) from exc
            if not isinstance(item, dict):
                raise DatasetValidationError(
                    f"Line {line_num} of {path.name} must be a JSON object, got {type(item).__name__}"
                )
            records.append(item)
    return _validate_and_normalize_records(records, source_name=path.name)


def _load_csv(path: Path) -> List[Dict[str, str]]:
    records = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise DatasetValidationError(f"CSV file is empty or missing headers: {path.name}")
        
        # Check required columns (case-insensitive header mapping)
        header_map = {col.lower().strip(): col for col in reader.fieldnames if col}
        missing = [rf for rf in REQUIRED_FIELDS if rf not in header_map]
        if missing:
            raise DatasetValidationError(
                f"CSV {path.name} missing required columns: {missing}. Available: {list(reader.fieldnames)}"
            )

        for row_idx, row in enumerate(reader, start=2):
            record = {
                "context": (row.get(header_map["context"]) or "").strip(),
                "question": (row.get(header_map["question"]) or "").strip(),
                "answer": (row.get(header_map["answer"]) or "").strip(),
            }
            records.append(record)
    return _validate_and_normalize_records(records, source_name=path.name)


def _validate_and_normalize_records(
    raw_records: List[Dict[str, Any]], source_name: str
) -> List[Dict[str, str]]:
    if not raw_records:
        raise DatasetValidationError(f"Dataset {source_name} is empty (0 valid records).")

    normalized = []
    errors = []

    for idx, raw in enumerate(raw_records):
        if not isinstance(raw, dict):
            errors.append(f"Record index {idx}: expected object, got {type(raw).__name__}")
            continue

        # Case-insensitive key lookup
        lowered = {str(k).lower().strip(): v for k, v in raw.items()}
        missing = [f for f in REQUIRED_FIELDS if f not in lowered]
        if missing:
            errors.append(f"Record index {idx}: missing required fields {missing}")
            continue

        context = str(lowered.get("context") or "").strip()
        question = str(lowered.get("question") or "").strip()
        answer = str(lowered.get("answer") or "").strip()

        if not context:
            errors.append(f"Record index {idx}: 'context' is empty.")
        if not question:
            errors.append(f"Record index {idx}: 'question' is empty.")
        if not answer:
            errors.append(f"Record index {idx}: 'answer' is empty.")

        if context and question and answer:
            normalized.append({
                "context": context,
                "question": question,
                "answer": answer,
            })

    if errors:
        max_preview = 5
        err_msg = "\n".join(errors[:max_preview])
        if len(errors) > max_preview:
            err_msg += f"\n... and {len(errors) - max_preview} more validation errors."
        raise DatasetValidationError(
            f"Dataset validation failed for {source_name} ({len(errors)} errors):\n{err_msg}"
        )

    return normalized


def split_dataset(
    records: List[Dict[str, str]],
    val_ratio: float = 0.1,
    seed: int = 42,
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Deterministically split records into training and validation sets without leakage.
    """
    if not (0.0 <= val_ratio < 1.0):
        raise ValueError(f"val_ratio must be in [0.0, 1.0), got {val_ratio}")

    if val_ratio == 0.0 or len(records) < 2:
        return records, []

    rng = random.Random(seed)
    shuffled = records.copy()
    rng.shuffle(shuffled)

    val_size = max(1, int(len(shuffled) * val_ratio))
    val_set = shuffled[:val_size]
    train_set = shuffled[val_size:]
    return train_set, val_set

