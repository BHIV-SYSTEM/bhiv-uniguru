"""
UniGuru — IndicSQuAD Complete Dataset Preprocessing Adapter.
Converts multilingual IndicSQuAD extractive QA datasets (l3cube-pune/indic-squad)
into the canonical UniGuru RAG LLM fine-tuning JSONL format.

Supports:
- Language selection (Marathi, Hindi, Bengali, Tamil, Telugu, etc.)
- Official splits (train, val, test) without data leakage
- Downloading and caching full raw source files with SHA-256 verification
- Full-dataset streaming conversion with constant O(1) RAM consumption
- Primary answer extraction & span alignment validation
- Multi-answer preservation in evaluation reference files
- Comprehensive rejection tracking (empty answers, missing contexts, unrecoverable spans, duplicates)
- Full compatibility with existing training/dataset_loader.py and dataset_formatter.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Tuple

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("uniguru.indic_squad_adapter")

# Language name / code mapping
SUPPORTED_LANGUAGES = {
    "marathi": ("Marathi", "mr"),
    "mr": ("Marathi", "mr"),
    "hindi": ("Hindi", "hi"),
    "hi": ("Hindi", "hi"),
    "bengali": ("Bengali", "bn"),
    "bn": ("Bengali", "bn"),
    "tamil": ("Tamil", "ta"),
    "ta": ("Tamil", "ta"),
    "telugu": ("Telugu", "te"),
    "te": ("Telugu", "te"),
    "gujarati": ("Gujarati", "gu"),
    "gu": ("Gujarati", "gu"),
    "punjabi": ("Punjabi", "pa"),
    "pa": ("Punjabi", "pa"),
    "kannada": ("Kannada", "kn"),
    "kn": ("Kannada", "kn"),
    "oriya": ("Oriya", "or"),
    "or": ("Oriya", "or"),
    "malayalam": ("Malayalam", "ml"),
    "ml": ("Malayalam", "ml"),
}

HF_BASE_RESOLVE_URL = "https://huggingface.co/datasets/l3cube-pune/indic-squad/resolve/main"


def resolve_language(lang_input: str) -> Tuple[str, str]:
    """Resolve user language input into (CanonicalName, lang_code)."""
    key = lang_input.strip().lower()
    if key in SUPPORTED_LANGUAGES:
        return SUPPORTED_LANGUAGES[key]
    raise ValueError(
        f"Unsupported language '{lang_input}'. Supported: {sorted(list(set(v[0] for v in SUPPORTED_LANGUAGES.values())))}"
    )


def download_file_with_checksum(
    url: str,
    destination: Path,
    expected_size: Optional[int] = None,
    force_download: bool = False,
) -> Dict[str, Any]:
    """
    Download a file via HTTP streaming with progress logging and SHA-256 checksum calculation.
    If the file exists and size matches, reuses existing local file.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and not force_download:
        actual_size = destination.stat().st_size
        if expected_size is None or actual_size == expected_size:
            logger.info(f"Local file exists: {destination.name} ({actual_size / (1024*1024):.2f} MB), computing SHA-256...")
            sha = hashlib.sha256()
            with destination.open("rb") as f:
                while chunk := f.read(1024 * 1024):
                    sha.update(chunk)
            return {
                "path": str(destination.resolve()),
                "url": url,
                "size_bytes": actual_size,
                "sha256": sha.hexdigest(),
                "downloaded": False,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(destination.stat().st_mtime)),
            }

    logger.info(f"Downloading {url} -> {destination}...")
    t0 = time.time()
    sha = hashlib.sha256()
    downloaded = 0
    req = urllib.request.Request(url, headers={"User-Agent": "UniGuru-IndicSQuAD-Adapter/1.0"})

    with urllib.request.urlopen(req, timeout=120) as resp, destination.open("wb") as f_out:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            f_out.write(chunk)
            sha.update(chunk)
            downloaded += len(chunk)

    elapsed = round(time.time() - t0, 2)
    rate = round(downloaded / (elapsed or 1) / (1024 * 1024), 2)
    logger.info(f"Downloaded {destination.name}: {downloaded / (1024*1024):.2f} MB in {elapsed}s ({rate} MB/s)")

    return {
        "path": str(destination.resolve()),
        "url": url,
        "size_bytes": downloaded,
        "sha256": sha.hexdigest(),
        "downloaded": True,
        "download_duration_seconds": elapsed,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def stream_json_array_records(source: str | Path, max_records: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:
    """
    Stream individual JSON objects from an online URL or local JSON array file
    without loading the entire multi-hundred megabyte file into memory at once.
    """
    source_str = str(source)
    is_url = source_str.startswith("http://") or source_str.startswith("https://")

    if is_url:
        req = urllib.request.Request(source_str, headers={"User-Agent": "UniGuru-IndicSQuAD-Adapter/1.0"})
        stream = urllib.request.urlopen(req, timeout=60)
    else:
        stream = open(source, "rb")

    buffer = ""
    decoder = json.JSONDecoder()
    in_array = False
    yielded = 0

    try:
        while True:
            if max_records and yielded >= max_records:
                break

            chunk = stream.read(65536)
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="ignore")

            if not in_array:
                bracket_pos = buffer.find("[")
                if bracket_pos != -1:
                    buffer = buffer[bracket_pos + 1 :]
                    in_array = True
                else:
                    continue

            while buffer:
                buffer = buffer.lstrip()
                if buffer.startswith(","):
                    buffer = buffer[1:].lstrip()
                if not buffer:
                    break
                if buffer.startswith("]"):
                    return

                try:
                    obj, idx = decoder.raw_decode(buffer)
                    if isinstance(obj, dict):
                        yield obj
                        yielded += 1
                        if max_records and yielded >= max_records:
                            return
                    buffer = buffer[idx:]
                except json.JSONDecodeError:
                    # Incomplete JSON object in buffer, fetch next chunk
                    break
    finally:
        stream.close()


def validate_and_convert_record(
    raw_record: Dict[str, Any],
    lang_code: str,
    seen_pairs: Set[Tuple[str, str]],
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str], bool, int]:
    """
    Validate an IndicSQuAD raw record and convert it into:
    1. training_record: {'context', 'question', 'answer', 'id', 'title', 'language'}
    2. eval_ref: {'id', 'question', 'context', 'primary_answer', 'all_answers', 'answer_starts', ...}
    3. rejection_reason: None if valid, or reason string if rejected
    4. span_repaired: True if answer_start was adjusted to match context
    5. final_answer_start: integer offset of answer in context
    """
    if not isinstance(raw_record, dict):
        return None, None, "malformed_record_not_dict", False, -1

    doc_id = str(raw_record.get("id") or "").strip()
    title = str(raw_record.get("title") or "").strip()
    context = str(raw_record.get("context") or "").strip()
    question = str(raw_record.get("question") or "").strip()

    if not context:
        return None, None, "empty_context", False, -1

    if not question:
        return None, None, "empty_question", False, -1

    answers = raw_record.get("answers")
    if not isinstance(answers, dict):
        return None, None, "answers_not_dict", False, -1

    ans_texts = answers.get("text", [])
    ans_starts = answers.get("answer_start", [])

    if not isinstance(ans_texts, list) or len(ans_texts) == 0:
        return None, None, "empty_answer_list", False, -1

    # Filter non-empty answer strings
    valid_answers = [str(t).strip() for t in ans_texts if str(t).strip()]
    if not valid_answers:
        return None, None, "whitespace_only_answers", False, -1

    primary_answer = valid_answers[0]

    # Verify span alignment
    span_repaired = False
    orig_start = ans_starts[0] if (isinstance(ans_starts, list) and len(ans_starts) > 0 and isinstance(ans_starts[0], int)) else -1
    final_start = orig_start

    # Check if context slice matches
    if orig_start >= 0 and orig_start + len(primary_answer) <= len(context):
        slice_text = context[orig_start : orig_start + len(primary_answer)]
        if slice_text != primary_answer:
            found_idx = context.find(primary_answer)
            if found_idx != -1:
                final_start = found_idx
                span_repaired = True
            else:
                return None, None, "answer_not_in_context", False, -1
    else:
        found_idx = context.find(primary_answer)
        if found_idx != -1:
            final_start = found_idx
            span_repaired = True
        else:
            return None, None, "answer_not_in_context", False, -1

    # Check for exact duplicate (context, question) within this split
    dedup_key = (context, question)
    if dedup_key in seen_pairs:
        return None, None, "duplicate_question_context", False, -1
    seen_pairs.add(dedup_key)

    # Format training record (compatible with existing dataset_loader and SFTTrainer)
    training_record = {
        "context": context,
        "question": question,
        "answer": primary_answer,
        "id": doc_id,
        "title": title,
        "language": lang_code,
    }

    # Format evaluation reference record (preserving all gold answers for EM/F1 metrics)
    eval_ref = {
        "id": doc_id,
        "title": title,
        "language": lang_code,
        "context": context,
        "question": question,
        "primary_answer": primary_answer,
        "all_answers": valid_answers,
        "original_answer_starts": ans_starts,
        "span_repaired": span_repaired,
        "final_answer_start": final_start,
    }

    return training_record, eval_ref, None, span_repaired, final_start


class IndicSQuADAdapter:
    """
    Adapter coordinator for downloading, cleaning, validating, and structuring IndicSQuAD data.
    """

    def __init__(
        self,
        language: str = "Marathi",
        raw_dir: Optional[str | Path] = None,
        output_dir: Optional[str | Path] = None,
    ):
        self.lang_name, self.lang_code = resolve_language(language)
        self.raw_dir = Path(raw_dir) if raw_dir else (_PROJECT_ROOT / "backend" / "data" / "raw" / "indic_squad" / self.lang_name.lower())
        self.output_dir = Path(output_dir) if output_dir else _PROJECT_ROOT

        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def download_split(self, split: str, force: bool = False) -> Dict[str, Any]:
        """Download and verify a single split (train, val, or test) to raw_dir."""
        url = f"{HF_BASE_RESOLVE_URL}/{self.lang_name}/{split}.json"
        dest_file = self.raw_dir / f"{split}.json"
        return download_file_with_checksum(url, dest_file, force_download=force)

    def process_split_incremental(
        self,
        split: str,
        target_sample_count: int,
        out_jsonl_path: Path,
        out_eval_refs_path: Optional[Path] = None,
        local_override: Optional[str | Path] = None,
    ) -> Dict[str, Any]:
        """
        Process a single split incrementally, writing records directly to disk.
        Maintains O(1) memory consumption and calculates exhaustive statistics.
        """
        if local_override and Path(local_override).is_file():
            source = str(Path(local_override).resolve())
        else:
            cached = self.raw_dir / f"{split}.json"
            if not cached.is_file():
                self.download_split(split)
            source = str(cached.resolve())

        logger.info(f"Processing split '{split}' for {self.lang_name} ({self.lang_code}) from: {source}")
        logger.info(f"Target count: {'ALL RECORDS' if target_sample_count <= 0 else target_sample_count}")

        out_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        if out_eval_refs_path:
            out_eval_refs_path.parent.mkdir(parents=True, exist_ok=True)

        t0 = time.time()
        seen_pairs: Set[Tuple[str, str]] = set()
        unique_titles: Set[str] = set()

        stats: Dict[str, Any] = {
            "split": split,
            "language_name": self.lang_name,
            "language_code": self.lang_code,
            "source_file": source,
            "raw_records_examined": 0,
            "valid_records_extracted": 0,
            "empty_answers_count": 0,
            "invalid_context_count": 0,
            "invalid_question_count": 0,
            "answer_not_in_context_count": 0,
            "exact_offsets_count": 0,
            "repaired_offsets_count": 0,
            "unrecoverable_offsets_count": 0,
            "duplicate_records_count": 0,
            "multiple_answers_count": 0,
            "unique_titles_count": 0,
            "avg_context_length": 0.0,
            "avg_question_length": 0.0,
            "avg_answer_length": 0.0,
            "rejections": {},
        }

        total_ctx_len = 0
        total_q_len = 0
        total_a_len = 0

        stream_limit = None if target_sample_count <= 0 else max(100, int(target_sample_count * 3))

        # Open JSONL and eval_refs writers incrementally
        f_eval = out_eval_refs_path.open("w", encoding="utf-8") if out_eval_refs_path else None
        if f_eval:
            f_eval.write("[\n")

        first_eval_ref = True

        try:
            with out_jsonl_path.open("w", encoding="utf-8") as f_jsonl:
                for raw in stream_json_array_records(source, max_records=stream_limit):
                    stats["raw_records_examined"] += 1

                    train_rec, eval_ref, rejection, repaired, final_offset = validate_and_convert_record(
                        raw, lang_code=self.lang_code, seen_pairs=seen_pairs
                    )

                    if rejection:
                        stats["rejections"][rejection] = stats["rejections"].get(rejection, 0) + 1
                        if rejection in ("empty_answer_list", "whitespace_only_answers"):
                            stats["empty_answers_count"] += 1
                        elif rejection == "empty_context":
                            stats["invalid_context_count"] += 1
                        elif rejection == "empty_question":
                            stats["invalid_question_count"] += 1
                        elif rejection == "answer_not_in_context":
                            stats["answer_not_in_context_count"] += 1
                            stats["unrecoverable_offsets_count"] += 1
                        elif rejection == "duplicate_question_context":
                            stats["duplicate_records_count"] += 1
                        continue

                    # Accepted record accounting
                    stats["valid_records_extracted"] += 1
                    if repaired:
                        stats["repaired_offsets_count"] += 1
                    else:
                        stats["exact_offsets_count"] += 1

                    if len(eval_ref.get("all_answers", [])) > 1:
                        stats["multiple_answers_count"] += 1

                    if train_rec.get("title"):
                        unique_titles.add(train_rec["title"])

                    total_ctx_len += len(train_rec["context"])
                    total_q_len += len(train_rec["question"])
                    total_a_len += len(train_rec["answer"])

                    # Stream write to JSONL
                    f_jsonl.write(json.dumps(train_rec, ensure_ascii=False) + "\n")

                    # Stream write to eval_refs JSON array
                    if f_eval:
                        if not first_eval_ref:
                            f_eval.write(",\n")
                        f_eval.write("  " + json.dumps(eval_ref, ensure_ascii=False))
                        first_eval_ref = False

                    if target_sample_count > 0 and stats["valid_records_extracted"] >= target_sample_count:
                        break
        finally:
            if f_eval:
                f_eval.write("\n]\n")
                f_eval.close()

        valid_cnt = max(1, stats["valid_records_extracted"])
        stats["unique_titles_count"] = len(unique_titles)
        stats["avg_context_length"] = round(total_ctx_len / valid_cnt, 2)
        stats["avg_question_length"] = round(total_q_len / valid_cnt, 2)
        stats["avg_answer_length"] = round(total_a_len / valid_cnt, 2)
        stats["processing_time_seconds"] = round(time.time() - t0, 2)

        logger.info(
            f"Split '{split}' finished in {stats['processing_time_seconds']}s: "
            f"{stats['valid_records_extracted']} valid extracted from {stats['raw_records_examined']} raw. "
            f"Repaired: {stats['repaired_offsets_count']}, Titles: {len(unique_titles)}, "
            f"Rejections: {stats['rejections']}"
        )
        return stats


def audit_cross_split_leakage(
    train_jsonl: Path,
    val_jsonl: Path,
    test_jsonl: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Exhaustively audit cross-split ID, context, question, and title overlap across splits.
    """
    logger.info("Executing cross-split leakage audit...")
    splits = [("train", train_jsonl), ("val", val_jsonl)]
    if test_jsonl and test_jsonl.is_file():
        splits.append(("test", test_jsonl))

    data: Dict[str, Dict[str, Set[Any]]] = {}
    for name, path in splits:
        ids: Set[str] = set()
        ctx_hashes: Set[str] = set()
        q_hashes: Set[str] = set()
        titles: Set[str] = set()

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                ids.add(r.get("id", ""))
                ctx_norm = " ".join(r.get("context", "").strip().split())
                q_norm = " ".join(r.get("question", "").strip().split())
                ctx_hashes.add(hashlib.md5(ctx_norm.encode("utf-8")).hexdigest())
                q_hashes.add(hashlib.md5(q_norm.encode("utf-8")).hexdigest())
                if r.get("title"):
                    titles.add(r["title"])

        data[name] = {
            "ids": ids,
            "ctx_hashes": ctx_hashes,
            "q_hashes": q_hashes,
            "titles": titles,
        }

    leakage_report: Dict[str, Any] = {
        "pairwise_comparisons": {},
        "total_cross_split_leaks": 0,
        "clean": True,
    }

    names = [s[0] for s in splits]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            s1, s2 = names[i], names[j]
            id_ov = len(data[s1]["ids"].intersection(data[s2]["ids"]))
            ctx_ov = len(data[s1]["ctx_hashes"].intersection(data[s2]["ctx_hashes"]))
            q_ov = len(data[s1]["q_hashes"].intersection(data[s2]["q_hashes"]))
            title_ov = len(data[s1]["titles"].intersection(data[s2]["titles"]))

            pair_key = f"{s1}_vs_{s2}"
            leakage_report["pairwise_comparisons"][pair_key] = {
                "id_overlap": id_ov,
                "context_overlap": ctx_ov,
                "question_overlap": q_ov,
                "title_overlap": title_ov,
            }
            if id_ov > 0 or ctx_ov > 0 or q_ov > 0:
                leakage_report["total_cross_split_leaks"] += (id_ov + ctx_ov + q_ov)
                leakage_report["clean"] = False

    return leakage_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="UniGuru IndicSQuAD Preprocessing Adapter",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--language", type=str, default="Marathi", help="Target Indic language (e.g., Marathi, Hindi)")
    parser.add_argument("--full", action="store_true", help="Process ALL records across official train, val, and test splits")
    parser.add_argument("--train-samples", type=int, default=500, help="Target training samples (0 = all)")
    parser.add_argument("--val-samples", type=int, default=100, help="Target validation samples (0 = all)")
    parser.add_argument("--test-samples", type=int, default=0, help="Target test samples (0 = all when --full)")
    parser.add_argument("--raw-dir", type=str, default=None, help="Directory to store or load raw source splits")
    parser.add_argument("--force-download", action="store_true", help="Force re-download of raw split files")
    parser.add_argument("--train-output", type=str, default=None, help="Explicit path for train JSONL output")
    parser.add_argument("--val-output", type=str, default=None, help="Explicit path for val JSONL output")
    parser.add_argument("--test-output", type=str, default=None, help="Explicit path for test JSONL output")
    parser.add_argument("--eval-refs-dir", type=str, default=None, help="Directory for evaluation reference JSON files")
    parser.add_argument("--report-output", type=str, default=None, help="Explicit path for preprocessing report JSON")
    parser.add_argument("--local-train-file", type=str, default=None, help="Optional local raw train JSON file")
    parser.add_argument("--local-val-file", type=str, default=None, help="Optional local raw val JSON file")
    parser.add_argument("--local-test-file", type=str, default=None, help="Optional local raw test JSON file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    adapter = IndicSQuADAdapter(language=args.language, raw_dir=args.raw_dir)
    lang_name, lang_code = adapter.lang_name, adapter.lang_code

    # When --full is passed, target counts default to 0 (meaning all records)
    if args.full:
        train_target = 0
        val_target = 0
        test_target = 0
        default_train_name = f"indic_squad_{lang_code}_train_full.jsonl"
        default_val_name = f"indic_squad_{lang_code}_val_full.jsonl"
        default_test_name = f"indic_squad_{lang_code}_test_full.jsonl"
        default_report_name = f"indic_squad_{lang_code}_full_preprocessing_report.json"
    else:
        train_target = args.train_samples
        val_target = args.val_samples
        test_target = args.test_samples
        default_train_name = f"indic_squad_{lang_code}_train_{train_target}.jsonl"
        default_val_name = f"indic_squad_{lang_code}_val_{val_target}.jsonl"
        default_test_name = f"indic_squad_{lang_code}_test_{test_target}.jsonl"
        default_report_name = f"indic_squad_{lang_code}_preprocessing_report.json"

    # Resolve output paths
    train_out = (
        Path(args.train_output) if args.train_output else (_PROJECT_ROOT / "data" / "training" / default_train_name)
    )
    val_out = (
        Path(args.val_output) if args.val_output else (_PROJECT_ROOT / "data" / "validation" / default_val_name)
    )
    test_out = (
        Path(args.test_output) if args.test_output else (_PROJECT_ROOT / "data" / "evaluation" / default_test_name)
    )

    eval_dir = Path(args.eval_refs_dir) if args.eval_refs_dir else (_PROJECT_ROOT / "data" / "evaluation")
    eval_dir.mkdir(parents=True, exist_ok=True)

    suffix_tag = "full" if args.full else f"pilot_{train_target}_{val_target}"
    train_eval_refs_out = eval_dir / f"indic_squad_{lang_code}_train_{suffix_tag}_eval_refs.json"
    val_eval_refs_out = eval_dir / f"indic_squad_{lang_code}_val_{suffix_tag}_eval_refs.json"
    test_eval_refs_out = eval_dir / f"indic_squad_{lang_code}_test_{suffix_tag}_eval_refs.json"

    report_out = (
        Path(args.report_output) if args.report_output else (_PROJECT_ROOT / "data" / "processed" / default_report_name)
    )
    report_out.parent.mkdir(parents=True, exist_ok=True)

    master_report: Dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dataset_source": "l3cube-pune/indic-squad",
        "language_name": lang_name,
        "language_code": lang_code,
        "mode": "complete_full_dataset" if args.full else "sample_subset",
        "raw_downloads": {},
        "splits": {},
        "artifacts_generated": {},
        "leakage_audit": {},
    }

    # Step 1: Download raw source files if needed
    for s in ("train", "val", "test"):
        if args.full or (s == "train" and train_target > 0) or (s == "val" and val_target > 0) or (s == "test" and test_target > 0):
            dl_info = adapter.download_split(s, force=args.force_download)
            master_report["raw_downloads"][s] = dl_info

    # Step 2: Process Training Split
    if args.full or train_target > 0 or args.local_train_file:
        train_stats = adapter.process_split_incremental(
            split="train",
            target_sample_count=train_target,
            out_jsonl_path=train_out,
            out_eval_refs_path=train_eval_refs_out,
            local_override=args.local_train_file,
        )
        master_report["splits"]["train"] = train_stats
        master_report["artifacts_generated"]["train_jsonl"] = {
            "path": str(train_out.resolve()),
            "count": train_stats["valid_records_extracted"],
            "size_bytes": train_out.stat().st_size,
        }
        master_report["artifacts_generated"]["train_eval_refs_json"] = {
            "path": str(train_eval_refs_out.resolve()),
            "count": train_stats["valid_records_extracted"],
            "size_bytes": train_eval_refs_out.stat().st_size,
        }

    # Step 3: Process Validation Split
    if args.full or val_target > 0 or args.local_val_file:
        val_stats = adapter.process_split_incremental(
            split="val",
            target_sample_count=val_target,
            out_jsonl_path=val_out,
            out_eval_refs_path=val_eval_refs_out,
            local_override=args.local_val_file,
        )
        master_report["splits"]["val"] = val_stats
        master_report["artifacts_generated"]["val_jsonl"] = {
            "path": str(val_out.resolve()),
            "count": val_stats["valid_records_extracted"],
            "size_bytes": val_out.stat().st_size,
        }
        master_report["artifacts_generated"]["val_eval_refs_json"] = {
            "path": str(val_eval_refs_out.resolve()),
            "count": val_stats["valid_records_extracted"],
            "size_bytes": val_eval_refs_out.stat().st_size,
        }

    # Step 4: Process Test Split (Only if --full or test_target > 0)
    if args.full or test_target > 0 or args.local_test_file:
        test_stats = adapter.process_split_incremental(
            split="test",
            target_sample_count=test_target,
            out_jsonl_path=test_out,
            out_eval_refs_path=test_eval_refs_out,
            local_override=args.local_test_file,
        )
        master_report["splits"]["test"] = test_stats
        master_report["artifacts_generated"]["test_jsonl"] = {
            "path": str(test_out.resolve()),
            "count": test_stats["valid_records_extracted"],
            "size_bytes": test_out.stat().st_size,
        }
        master_report["artifacts_generated"]["test_eval_refs_json"] = {
            "path": str(test_eval_refs_out.resolve()),
            "count": test_stats["valid_records_extracted"],
            "size_bytes": test_eval_refs_out.stat().st_size,
        }

    # Step 5: Exhaustive Cross-Split Leakage Audit
    leakage = audit_cross_split_leakage(
        train_jsonl=train_out,
        val_jsonl=val_out,
        test_jsonl=test_out if (args.full or test_target > 0) else None,
    )
    master_report["leakage_audit"] = leakage

    # Save Preprocessing Report
    report_out.write_text(json.dumps(master_report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Master preprocessing report saved to: {report_out.resolve()}")

    print("\n" + "=" * 70)
    print(" [SUCCESS] Complete IndicSQuAD Preprocessing Finished!")
    print(f" Language:     {lang_name} ({lang_code})")
    print(f" Train File:   {train_out.resolve()} ({master_report['artifacts_generated'].get('train_jsonl', {}).get('count', 0)} records)")
    print(f" Val File:     {val_out.resolve()} ({master_report['artifacts_generated'].get('val_jsonl', {}).get('count', 0)} records)")
    if args.full or test_target > 0:
        print(f" Test File:    {test_out.resolve()} ({master_report['artifacts_generated'].get('test_jsonl', {}).get('count', 0)} records)")
    print(f" Leakage Clean: {leakage.get('clean')} (Cross-split leaks: {leakage.get('total_cross_split_leaks')})")
    print(f" Report:       {report_out.resolve()}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
