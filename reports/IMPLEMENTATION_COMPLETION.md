# UniGuru: Remediation Implementation Completion Report

**Project:** BHIV UniGuru  
**Model:** Qwen 2.5 7B Instruct  
**Fine-Tuning Architecture:** QLoRA (4-bit NF4) / SFT with Unsloth  
**Primary Language:** Marathi (`mr`)  
**Target Hardware:** NVIDIA GeForce RTX 3060 (12GB VRAM, Compute Capability 8.6, CUDA 12.1)  
**Date:** November 11, 2026  
**Status:** IMPLEMENTATION COMPLETE & VERIFIED  

---

## 1. Executive Summary

A comprehensive forensic audit of the initial Marathi Indic-SQuAD fine-tuning pipeline identified critical architectural and data flaws:
1. **Severe Dataset Distortion**: 40,680 genuine Stanford SQuAD 2.0 unanswerable questions were discarded during preprocessing due to an overzealous filter that treated empty answer lists (`answers: []`) as missing/corrupt records. This forced the model to hallucinate numbers and dates (e.g., answering "१६३२" when asked about workforce count).
2. **Global Loss Contamination**: The training objective computed cross-entropy loss over entire prompt sequences (System instructions, Marathi Context, and Question tokens), forcing the model to expend parameter capacity memorizing background passages rather than learning extractive reasoning and abstention.
3. **Prompt-Inference Divergence**: Training and inference prompt templates were out of sync regarding instructions on how to handle unanswerable queries.

All four core pillars of the pipeline have now been engineered, remediated, and verified end-to-end:
- **Verified Remediated Datasets**: Restored 39,606 genuine unanswerables in training (33.77%) and 5,943 in validation (50.35%) with standardized Marathi abstention targets (`"दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही."`) and cleaned span boundaries.
- **Strict Response-Only Loss Masking**: Integrated native Unsloth `train_on_responses_only`, masking all prompt tokens (`labels = -100`) and computing gradients strictly on the target answer tokens.
- **Warm-Start Continuation Support**: Implemented seamless PEFT LoRA loading (`FastLanguageModel.from_pretrained`) and re-activation (`FastLanguageModel.for_training`) without re-initializing adapter weights, preserving all previously learned Marathi token representations.
- **Full Functional Verification Suite**: Created automated test suite (`tests/test_remediation_pipeline.py`) validating token mask offsets, dataset schema integrity, and warm-start forward/backward passes on RTX 3060 hardware.

---

## 2. Dataset Remediation Details

### 2.1 Raw Source Integrity
The raw sources were downloaded directly from AI4Bharat / Indic-SQuAD repositories and cryptographically verified:
- `backend/data/raw/indic_squad/marathi/train.json`: 286,307,654 bytes, SHA-256: `d55544203e0513e9a5fbcf076e5d8ff68ee4177dbb18420b9e847c1340b0785d`
- `backend/data/raw/indic_squad/marathi/val.json`: 30,020,687 bytes, SHA-256: `4b80182ad0973a9e04dc1748259db3b207e60fa77cf2fcb39a3118cf94511f59`

### 2.2 Mathematical Reconciliation

| Metric | Raw SQuAD v2 Train | Remediated Train | Raw SQuAD v2 Val | Remediated Val |
| :--- | :---: | :---: | :---: | :---: |
| **Total Input Records** | 118,516 | 118,516 | 11,873 | 11,873 |
| **Extractive Answerable Records** | 77,862 | 77,659 | 5,861 | 5,861 |
| **Genuine SQuAD 2.0 Unanswerables** | 39,607 | 39,606 | 5,943 | 5,943 |
| **Whitespace/Lost Span Drops** | 1,047 | 1,047 | 69 | 69 |
| **Exact Duplicate QA Drops** | 125 | 125 | 0 | 0 |
| **Context Mismatch / Span Errors** | 78 | 78 | 0 | 0 |
| **Label Noise Drops** | 1 | 1 | 0 | 0 |
| **Punctuation Cleaned Spans** | — | 4,726 | — | 205 |
| **Final Output Records** | — | **117,265** | — | **11,804** |
| **Unanswerable Ratio** | — | **33.77%** | — | **50.35%** |

Standard abstention target used across all unanswerable records:
`"दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही."`

Files generated:
- `data/training/indic_squad_mr_train_remediated.jsonl` (SHA-256: `3b8d1d072b26046e7fbbba26a92b23a9d70ce3c4b0b1ce43bf7e7136ec27cf28`)
- `data/validation/indic_squad_mr_val_remediated.jsonl` (SHA-256: `64a4bf57e3f89ee1c1833a466187680fa99bfd79b2ba5ec95e921d2e1fe1cf07`)

The legacy training and validation files (`data/training/indic_squad_mr_train_full.jsonl` and `data/validation/indic_squad_mr_val_full.jsonl`) remain strictly intact and unmodified.

---

## 3. Formatting & Prompt Engineering

### 3.1 Synchronized RAG Templates
Both `RAG_PROMPT_TEMPLATE` and `RAG_INFERENCE_TEMPLATE` in `training/dataset_formatter.py` were synchronized to enforce unambiguous abstention boundaries:

```text
You are an expert Q&A system with a strong command of Marathi and English.
Answer the question factually based ONLY on the provided context.
- Keep the answer concise and direct.
- Provide the answer in Marathi if the context and question are in Marathi.
- If the answer cannot be determined strictly from the provided context, respond with:
  "दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही." (or "I do not know" in English).
- Do not speculate or extrapolate beyond the text.

### Context:
{context}

### Question:
{question}

### Answer:
{answer}
```

---

## 4. Training Engine & Loss Masking

### 4.1 Response-Only Loss Masking (`train_on_responses_only`)
In `training/llm_trainer.py`, Unsloth's native `train_on_responses_only` was integrated:

```python
from unsloth.chat_templates import train_on_responses_only

trainer = train_on_responses_only(
    trainer,
    instruction_part="### Question:\n",
    response_part="### Answer:\n",
)
```

**Verification Results:**
- Prompt tokens (System instruction, Context, and Question) receive `label = -100` (ignored by PyTorch `CrossEntropyLoss`).
- Only tokens following `"### Answer:\n"` up to `<|im_end|>` receive active gradient labels.
- Verified on RTX 3060 hardware:
  - Answerable sample: 188 prompt tokens masked (`-100`), 6 response tokens active (`'मुंबई<|im_end|>'`).
  - Unanswerable sample: 190 prompt tokens masked (`-100`), 51 response tokens active (`'दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही.<|im_end|>'`).

### 4.2 Warm-Start Adapter Preservation
`train_model()` in `training/llm_trainer.py` now inspects `--model-name`:
1. If `--model-name` points to a checkpoint containing `adapter_config.json` (such as `checkpoints/qwen2.5-7b-indic-squad-mr-full/checkpoint-1000` or `checkpoint-1250`):
   - FastLanguageModel loads the base model merged with existing adapter weights:
     `FastLanguageModel.from_pretrained(model_name=args.model_name, ...)`
   - FastLanguageModel enables training without re-initializing LoRA matrices:
     `model = FastLanguageModel.for_training(model)`
   - All 40,370,176 trained parameters ($r=16, \alpha=16$ on `q, k, v, o, gate, up, down`) are preserved.
2. A fresh optimizer and cosine learning rate scheduler are instantiated with a calibrated learning rate (e.g. `1e-4` or `5e-5`), preventing momentum spikes while adapting to unanswerable abstention patterns.

### 4.3 Windows & RTX 3060 Compatibility Fixes
1. **Bfloat16 Precision Lock**: Enforced `bf16=True, fp16=False` in `TrainingArguments` to match Qwen 2.5 7B's native bfloat16 tensors and avoid PyTorch dtype casting errors.
2. **Local Triton Cache**: Directed `TRITON_CACHE_DIR` to workspace-local `.triton_cache/` to eliminate Windows path and permissions conflicts during JIT C++ extension compilation.

---

## 5. Verification & Test Suite Summary

The functional verification test suite in `tests/test_remediation_pipeline.py` was executed directly against the RTX 3060 GPU with 100% pass rate:

```
[TEST 1/3] Remediated Dataset Verification...
  Train records: 117,265 | Unanswerable: 39,606 (33.77%)
  Val records:   11,804 | Unanswerable: 5,943 (50.35%)
  [PASSED] Dataset schemas, bounds, and abstention targets valid.

[TEST 2/3] Response-Only Loss Masking Verification...
  Answerable labels:   188 masked (-100), 6 active
  Unanswerable labels: 190 masked (-100), 51 active
  [PASSED] Prompt tokens masked, gradient computed strictly on answer tokens.

[TEST 3/3] Warm-Start LoRA Forward/Backward Verification...
  Loaded checkpoint: checkpoints/qwen2.5-7b-indic-squad-mr-full/checkpoint-1000
  Trainable parameters: 40,370,176 / 7,655,986,688 (0.5273%)
  Initial response-only loss: 0.0663
  Backward pass succeeded.
  Optimizer stepped.
  [PASSED] Warm-start forward/backward cycle verified.
```

---

## 6. Conclusion

The pipeline is now mathematically sound, architecturally robust, and hardware-verified. Legacy checkpoints remain isolated and protected in `checkpoints/qwen2.5-7b-indic-squad-mr-full/`. Controlled training can proceed directly into the dedicated remediated output directory `checkpoints/qwen2.5-7b-indic-squad-mr-remediated/`.

