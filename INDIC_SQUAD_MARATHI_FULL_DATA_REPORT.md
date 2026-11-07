# UniGuru — Complete Marathi IndicSQuAD Preprocessing Report

**Target Language**: Marathi (`mr`)  
**Source Dataset**: [`l3cube-pune/indic-squad`](https://huggingface.co/datasets/l3cube-pune/indic-squad)  
**Execution Environment**: Python 3.14.3 / UniGuru Preprocessing Pipeline  
**Execution Mode**: Full Dataset Preprocessing (`--full`)  

---

## 1. Executive Summary

The complete Marathi IndicSQuAD dataset has been extracted, validated, and formatted into canonical RAG instruction datasets ready for fine-tuning the Qwen 2.5 7B Instruct model with 4-bit QLoRA on the target NVIDIA RTX 3060 (12GB) machine.

- **Total Source Records Examined**: **142,192**
- **Total Valid Answerable Records Extracted**: **91,345**
  - **Training Split**: **77,660** records
  - **Validation Split**: **5,861** records
  - **Test Split**: **7,824** records
- **Total Rejections Filtered**: **50,847** (primarily 49,442 SQuAD 2.0 unanswerable questions)
- **Character Offset Accuracy**: **99.25%** exact original offsets; **0.75%** (688 records) cleanly repaired via context boundary alignment; **0%** misaligned answers admitted.
- **Cross-Split Leakage**: **Zero ID leakage**, **Zero context leakage between Train and Validation**.

---

## 2. Source Dataset Verification & Preserved Raw Caches

All three official splits were downloaded directly from the Hugging Face Git LFS resolve endpoint and preserved in the dedicated raw data directory `backend/data/raw/indic_squad/marathi/`.

| Split | Source URL | File Size | Records | SHA-256 Checksum |
|---|---|---|---|---|
| **Train** | `.../Marathi/train.json` | 286,307,654 bytes (273.04 MB) | 118,516 | `d5554420113b9976c39e19d5ab15e201044d572aa839ac92a8482491960b23f9` |
| **Validation** | `.../Marathi/val.json` | 30,020,687 bytes (28.63 MB) | 11,873 | `4b80182a9690ba62f1549dcc60155f5bce60be4c5c31eaf15a79ba7a2f3b6b67` |
| **Test** | `.../Marathi/test.json` | 28,689,371 bytes (27.36 MB) | 11,803 | `41954e11bf39e5ef14a8c9377c24c6c79ee47183f2ac30d0beeaffe65cb4db59` |
| **Total Raw** | — | **345,017,712 bytes (329.03 MB)** | **142,192** | — |

*Note: Existing pilot caches (`raw_train_710.json` and `raw_val_200.json`) remain intact and unaltered.*

---

## 3. Generated Artifacts & File Deliverables

The processed outputs were generated using streaming incremental writers, maintaining $O(1)$ memory consumption throughout the process:

| Artifact | File Path | Record Count | File Size | Description |
|---|---|---|---|---|
| **Training JSONL** | `data/training/indic_squad_mr_train_full.jsonl` | **77,660** | 178,485,708 B (170.2 MB) | Training pairs (`context`, `question`, `answer`, `id`, `title`, `language`). |
| **Training Eval Refs** | `data/evaluation/indic_squad_mr_train_full_eval_refs.json` | **77,660** | 191,752,962 B (182.9 MB) | Complete reference metadata for training pairs. |
| **Validation JSONL** | `data/validation/indic_squad_mr_val_full.jsonl` | **5,861** | 14,241,668 B (13.6 MB) | Held-out validation pairs for loss and checkpointing. |
| **Validation Eval Refs** | `data/evaluation/indic_squad_mr_val_full_eval_refs.json` | **5,861** | 15,248,938 B (14.5 MB) | Ground-truth answer references for EM and Token F1 evaluation. |
| **Test JSONL** | `data/evaluation/indic_squad_mr_test_full.jsonl` | **7,824** | 17,905,000 B (17.1 MB) | Final held-out test split (untouched during training). |
| **Test Eval Refs** | `data/evaluation/indic_squad_mr_test_full_eval_refs.json` | **7,824** | 19,239,203 B (18.3 MB) | Final benchmark evaluation references. |
| **Audit Report** | `data/processed/indic_squad_mr_full_preprocessing_report.json` | — | 5,160 B | Full machine-readable processing statistics. |

---

## 4. Split-by-Split Quality & Rejection Analysis

```
Source Records (142,192)
       │
       ├──► Accepted (91,345) ──► 77,660 Train  |  5,861 Val  |  7,824 Test
       │
       └──► Rejected (50,847)
               ├── 49,442 Empty Answer List (SQuAD 2.0 Unanswerables)
               ├── 1,191 Whitespace Only
               ├── 123 Intra-Split Duplicates
               └── 91 Answer Not in Context (Unrecoverable Spans)
```

### Detailed Statistics Table

| Metric | Training Split | Validation Split | Test Split | Total Across Splits |
|---|---|---|---|---|
| **Raw Records Examined** | 118,516 | 11,873 | 11,803 | **142,192** |
| **Valid Records Extracted** | **77,660** | **5,861** | **7,824** | **91,345** |
| **Exact Offsets** | 77,073 (99.24%) | 5,817 (99.25%) | 7,767 (99.27%) | **90,657 (99.25%)** |
| **Repaired Offsets** | 587 (0.76%) | 44 (0.75%) | 57 (0.73%) | **688 (0.75%)** |
| **Unrecoverable Offsets (Rejected)** | 78 | 6 | 7 | **91** |
| **Empty Answers (SQuAD 2.0)** | 39,632 | 5,945 | 3,865 | **49,442** |
| **Whitespace-Only Answers** | 1,048 | 51 | 92 | **1,191** |
| **Duplicate (Context, Question)** | 98 | 10 | 15 | **123** |
| **Unique Article Titles** | **466** | **38** | **423** | — |
| **Avg Context Length (Chars)** | 721.67 | 767.77 | 718.62 | **724.36** |
| **Avg Question Length (Chars)** | 56.17 | 57.80 | 56.09 | **56.26** |
| **Avg Answer Length (Chars)** | 19.96 | 20.28 | 19.86 | **19.97** |
| **Processing Time** | 3.54s | 0.40s | 0.35s | **4.29s** |

---

## 5. Cross-Split Leakage Audit

A comprehensive pairwise audit checked for leakage across source IDs, context hashes, question hashes, and Wikipedia article titles:

| Pairwise Comparison | Source ID Overlap | Context Overlap | Question Overlap | Article Title Overlap | Leakage Assessment |
|---|---|---|---|---|---|
| **Train vs. Val** | **0** | **0** | 5 | **0** | **Zero Leakage**: Clean separate sets. The 5 question overlaps are standard generic queries (e.g. *"त्याचे नाव काय होते?"*) with completely disjoint contexts. |
| **Train vs. Test** | **0** | 1 | 12 | 422 | **Official Upstream Design**: IndicSQuAD/SQuAD authors partitioned paragraphs from the same 422 articles into Train and Test. Exactly 1 identical context paragraph was found across both splits in the upstream dataset. |
| **Val vs. Test** | **0** | **0** | **0** | **0** | **Zero Leakage**: Validation and Test splits are 100% disjoint across all articles, contexts, and questions. |

---

## 6. Verification & Test Evidence

### A. Unit & Pipeline Regression Suites
All 61 test cases passed cleanly:
1. `tests/test_indic_squad_adapter.py` $\rightarrow$ **12/12 passed** in 0.19s.
2. `tests/test_training_pipeline.py` + `tests/test_data_preprocessing_pipeline.py` $\rightarrow$ **30/30 passed** in 2.96s.
3. `backend/tests/test_auth_service.py` + `backend/tests/test_sanskrit_decoder.py` $\rightarrow$ **19/19 passed** in 6.39s.

### B. Full-Dataset Training Pipeline Dry-Run
Executed the official training dry-run using the complete training and validation sets:
```bash
python training/llm_trainer.py \
  --dataset data/training/indic_squad_mr_train_full.jsonl \
  --val-dataset data/validation/indic_squad_mr_val_full.jsonl \
  --dry-run
```

**Result**:
- Successfully loaded and validated **77,660 training records** and **5,861 validation records** in **1.07 seconds**.
- Formatted sample Marathi instruction prompt verified.
- Confirmed output directory destinations.
- Exited with code 0: **`[DRY-RUN SUCCESS] Pipeline configuration and datasets are 100% VALID.`**

---

## 7. Data Quality Findings & Caveats

1. **SQuAD 2.0 Unanswerables**: Approximately 35% of records in the raw source files are unanswerable questions (`answers.text == []`). These were correctly filtered out, leaving 91,345 grounded, answerable pairs across the splits.
2. **Upstream Machine-Translation Punctuation Artifacts**: A small fraction (~0.7%) of upstream answer spans contain punctuation artifacts (such as unbalanced parentheses, e.g. `'टेलिव्हिजन स्टेशन (आयटीव्ही'`). In accordance with Requirement 4, the adapter preserves Marathi Unicode characters and exact original answers without inventing or truncating text.
3. **Traceability**: Every record in the JSONL and evaluation reference files retains its original `id`, `title`, and character offset tracking for 100% auditing back to the raw source data.

---

## 8. Exact Commands for GPU Training on RTX 3060

When transferring to the target machine with an NVIDIA GeForce RTX 3060 (12GB VRAM):

```bash
# 1. Activate isolated training environment
source venv-training/bin/activate  # (or .\venv-training\Scripts\activate on Windows)

# 2. Verify GPU detection & BF16 support
python -c "import torch; print(torch.cuda.get_device_name(0), 'VRAM:', round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2), 'GB')"

# 3. Quick sanity check on complete dataset (dry-run)
python training/llm_trainer.py \
  --dataset data/training/indic_squad_mr_train_full.jsonl \
  --val-dataset data/validation/indic_squad_mr_val_full.jsonl \
  --dry-run

# 4. Launch Full Fine-Tuning Run (1 Epoch = ~9,707 steps at effective batch size 8)
python training/llm_trainer.py \
  --dataset data/training/indic_squad_mr_train_full.jsonl \
  --val-dataset data/validation/indic_squad_mr_val_full.jsonl \
  --epochs 1 \
  --batch-size 2 \
  --max-seq-length 1536 \
  --output-dir checkpoints/qwen2.5-7b-indic-squad-mr-full \
  --adapter-dir models/adapters/qwen2.5-7b-indic-squad-mr-full
```

