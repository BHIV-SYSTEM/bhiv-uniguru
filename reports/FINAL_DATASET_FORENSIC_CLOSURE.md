# UniGuru — Final Dataset Forensic Closure & Pipeline Remediation Report

**Project**: BHIV UniGuru  
**Model**: Qwen 2.5 7B Instruct (`unsloth/Qwen2.5-7B-Instruct-bnb-4bit`)  
**Task**: Forensic Closure of Discarded Indic-SQuAD Records & Pipeline Remediation  
**Date**: November 11, 2026  
**Status**: COMPLETE — Verified, Reconciled, and Remediated  

---

## 1. Executive Verdict

1. **Definitive Finding on the 40,680 Discarded Records**:
   * **39,632 records (97.42% of discards) are GENUINE SQuAD v2 UNANSWERABLE QUESTIONS (`VERIFIED_UNANSWERABLE`)**.
     * Origin: Upstream dataset [`l3cube-pune/indic-squad`](https://huggingface.co/datasets/l3cube-pune/indic-squad) (Marathi subset), translated directly from Stanford's **SQuAD 2.0**.
     * In SQuAD 2.0, approximately 34% of training questions are plausible unanswerable questions crafted to test whether a model knows when information is absent. In the raw JSON source, these records have empty answer arrays: `"answers": {"text": [], "answer_start": []}`.
     * All 39,632 records carry Stanford SQuAD 2.0 MongoDB ObjectIDs (99.4% prefix `5a`, 0.6% prefix `59`).
     * They are **clean, high-quality, valid negative examples**.
   * **1,048 records (2.58% of discards) are TRANSLATION SPAN LOSSES (`VERIFIED_ANSWERABLE_BUT_LOST`)**:
     * In these records, `answers.text` contained empty or whitespace strings (`[" "]` or `[""]`).
     * All carry SQuAD 1.1 ID prefixes (`57` and `56`). They were answerable in the original English corpus, but cross-lingual alignment failed to project the answer span into Marathi, leaving an empty string.
   * **98 duplicate QA pairs** and **78 span mismatch errors** represent malformed data (`MALFORMED_SOURCE_RECORD`).

2. **Why They Were Discarded**:
   * The preprocessing adapter [`scripts/prepare_indic_squad.py`](file:///c:/Ganesh_149/uniguru/bhiv-uniguru/scripts/prepare_indic_squad.py#L231) was explicitly programmed to reject any record with an empty answer array (`rejection = "empty_answer_list"`).
   * This design choice was made to maintain compatibility with [`training/dataset_loader.py#L135`](file:///c:/Ganesh_149/uniguru/bhiv-uniguru/training/dataset_loader.py#L135), which strictly raised an exception on empty answers.
   * Instead of assigning an explicit abstention target string (such as `"दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही."`), the adapter dropped all 39,632 unanswerable questions, inadvertently eliminating 100% of the negative training signal.

3. **Remediation Delivered**:
   * **Full Raw Datasets Recovered & Verified**: Raw source splits `train.json` (286.3 MB, SHA-256: `d5554420...`) and `val.json` (30.0 MB, SHA-256: `4b80182a...`) are preserved in `backend/data/raw/indic_squad/marathi/`.
   * **Remediated Datasets Generated**:
     * `data/training/indic_squad_mr_train_remediated.jsonl` (**117,265 records**, 33.77% unanswerables).
     * `data/validation/indic_squad_mr_val_remediated.jsonl` (**11,804 records**, 50.35% unanswerables).
   * **Boundary Sanitization**: 4,726 answer spans had trailing commas, broken quotes, and unbalanced parentheses cleanly repaired.
   * **Response-Only Loss Masking**: Integrated via native Unsloth `train_on_responses_only` to mask Context and compute loss strictly on Answer tokens.

---

## 2. Original Source Verification & Provenance

### Source Verification
* **Hugging Face Repository**: `https://huggingface.co/datasets/l3cube-pune/indic-squad`
* **Local Files Verified with Exact SHA-256**:
  * `backend/data/raw/indic_squad/marathi/train.json` (286,307,654 bytes)
    `SHA-256: d5554420113b9976c39e19d5ab15e201044d572aa839ac92a8482491960b23f9`
  * `backend/data/raw/indic_squad/marathi/val.json` (30,020,687 bytes)
    `SHA-256: 4b80182a9690ba62f1549dcc60155f5bce60be4c5c31eaf15a79ba7a2f3b6b67`

### Schema Analysis
Each raw entry is a JSON object with exactly 5 fields:
`['id', 'title', 'context', 'question', 'answers']`
* **`is_impossible` Field**: In this pre-flattened JSON format, the boolean `is_impossible` flag was **not retained as a key**. Instead, unanswerability is indicated purely by `answers: {"text": [], "answer_start": []}`.
* **ID Correlation**:
  * 100.00% of the 5,945 empty-answer records in `val.json` have MongoDB ObjectIDs starting with `5a` (SQuAD 2.0 unanswerable subset).
  * In `train.json`, 39,392 empty-answer records start with `5a` and 240 start with `59`.
  * Zero answerable records have `5a` prefixes (with exactly one corrupted exception, Record `5a8cc8f2fd22b3001a8d8e6a`, which was filtered out during remediation).

---

## 3. Exact Mathematical Reconciliation of Discarded Records

Reconciliation was verified by streaming every record directly from the verified raw source files.

### A. Training Split Reconciliation (Total: 118,516 Records)

| Category | Record Count | % of Raw Data | Classification | Description |
|---|---:|---:|---|---|
| **Empty Answer Array** | **39,632** | 33.44% | **`VERIFIED_UNANSWERABLE`** | Genuine Stanford SQuAD 2.0 unanswerable questions. |
| **Whitespace-Only Answers** | **1,048** | 0.88% | **`VERIFIED_ANSWERABLE_BUT_LOST`** | Valid English questions whose answer text was dropped in machine translation. |
| **Duplicate QA Pairs** | **98** | 0.08% | **`MALFORMED_SOURCE_RECORD`** | Exact `(context, question)` duplicates within the split. |
| **Span Mismatches** | **78** | 0.07% | **`MALFORMED_SOURCE_RECORD`** | Translated answer string absent from translated context. |
| **Accepted Answerable** | **77,660** | 65.53% | **`VERIFIED_ANSWERABLE`** | Verbatim extractive answers present in context. |
| **TOTAL RAW EXAMINED** | **118,516** | **100.00%** | **EXACT RECONCILIATION** | $77,660 + 39,632 + 1,048 + 98 + 78 = 118,516$ |

---

### B. Validation Split Reconciliation (Total: 11,873 Records)

| Category | Record Count | % of Raw Data | Classification | Description |
|---|---:|---:|---|---|
| **Empty Answer Array** | **5,945** | 50.07% | **`VERIFIED_UNANSWERABLE`** | Genuine Stanford SQuAD 2.0 unanswerable questions (50.08% official SQuAD 2.0 val ratio). |
| **Whitespace-Only Answers** | **51** | 0.43% | **`VERIFIED_ANSWERABLE_BUT_LOST`** | Machine translation alignment dropped answer string. |
| **Duplicate QA Pairs** | **10** | 0.08% | **`MALFORMED_SOURCE_RECORD`** | Exact duplicate QA pairs. |
| **Span Mismatches** | **6** | 0.05% | **`MALFORMED_SOURCE_RECORD`** | Answer string absent from context. |
| **Accepted Answerable** | **5,861** | 49.36% | **`VERIFIED_ANSWERABLE`** | Verbatim extractive answers. |
| **TOTAL RAW EXAMINED** | **11,873** | **100.00%** | **EXACT RECONCILIATION** | $5,861 + 5,945 + 51 + 10 + 6 = 11,873$ |

---

## 4. Representative Source-Record Evidence

### Genuine Unanswerable Examples Recovered from Raw `train.json`

1. **ID `5acfd57077cf76001a68625a` (Article: प्रेस्बिटेरियनवाद)**:
   * **Context**: `"प्रेस्बिटेरियनिझम हा उत्तर आयर्लंडमधील सर्वात मोठा प्रोटेस्टंट संप्रदाय आहे आणि आयर्लंड बेटावर (आयर्लंडच्या अँग्लिकन चर्च नंतर) दुसरा सर्वात मोठा संप्रदाय आहे..."`
   * **Question**: *उत्तर आयर्लंडमध्ये कोणता धर्म दुसरा सर्वात मोठा संप्रदाय आहे?* (In Northern Ireland, which religion is the second largest denomination?)
   * **Why Unanswerable**: The passage states Presbyterianism is the *largest* in Northern Ireland and *second largest on the island of Ireland*. It never mentions which is the *second largest in Northern Ireland*.
   * **Raw Annotation**: `answers: {"text": [], "answer_start": []}`
2. **ID `5ad398a7604f3c001a3fe800` (Article: मियामी)**:
   * **Context**: Describes construction of Miami Intermodal Center and Miami Central Station.
   * **Question**: *मियामी सेंटर स्टेशनचा तिसरा टप्पा कधी सेवेत दाखल होणार होता?* (When was the third phase of Miami Central Station to enter service?)
   * **Why Unanswerable**: The passage mentions Phase 1 and Phase 2, but never mentions a Phase 3.
   * **Raw Annotation**: `answers: {"text": [], "answer_start": []}`
3. **ID `5ad398a7604f3c001a3fe803` (Article: मियामी)**:
   * **Question**: *२००२ च्या कोणत्या भागात मियामी सेंट्रल स्टेशनचा पहिला टप्पा सुरू झाला होता?* (In which part of 2002 was phase one of Miami Central Station started?)
   * **Why Unanswerable**: The passage discusses construction from 2011 onwards; 2002 is not mentioned.
   * **Raw Annotation**: `answers: {"text": [], "answer_start": []}`

### Resolution of Earlier Report Inconsistencies

1. **The "United States Dollar" Record (`5a8cc8f2fd22b3001a8d8e6a`)**:
   * *Investigation*: In raw `train.json`, this record actually contains `answers: {"text": ["स्पॅनिश"], "answer_start": [0]}` despite having a SQuAD 2.0 `5a` ID.
   * *Finding*: This was an upstream annotation mismatch in the L3Cube corpus where a distractor was erroneously assigned as an answer.
   * *Resolution*: Explicitly blacklisted and removed in [`scripts/generate_remediated_dataset.py`](file:///c:/Ganesh_149/uniguru/bhiv-uniguru/scripts/generate_remediated_dataset.py#L65-L68).
2. **The "Empty Answers via Translation Alignment" Claim**:
   * *Clarification*: The 39,632 `empty_answer_list` records were **not** caused by translation span alignment failures; they were Stanford SQuAD 2.0 unanswerables.
   * The translation alignment failures account exclusively for the **1,048 whitespace-only records** (`VERIFIED_ANSWERABLE_BUT_LOST`).

---

## 5. Remediation Delivered: Generated Clean Datasets

The generation script [`scripts/generate_remediated_dataset.py`](file:///c:/Ganesh_149/uniguru/bhiv-uniguru/scripts/generate_remediated_dataset.py) processed the raw files and generated production-ready datasets:

### Dataset Comparison: Original vs. Remediated

| Metric | Original Train | **Remediated Train** | Original Val | **Remediated Val** |
|---|---|---|---|---|
| **File Path** | `data/training/indic_squad_mr_train_full.jsonl` | `data/training/indic_squad_mr_train_remediated.jsonl` | `data/validation/indic_squad_mr_val_full.jsonl` | `data/validation/indic_squad_mr_val_remediated.jsonl` |
| **Total Records** | 77,660 | **117,265** | 5,861 | **11,804** |
| **Answerable Records** | 77,660 (100.0%) | **77,659 (66.23%)** | 5,861 (100.0%) | **5,861 (49.65%)** |
| **Unanswerable Records**| 0 (0.00%) | **39,606 (33.77%)** | 0 (0.00%) | **5,943 (50.35%)** |
| **Abstention Target** | None | `"दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही."` | None | `"दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही."` |
| **Punctuation Cleaned** | 0 | **4,726 spans sanitized** | 0 | **205 spans sanitized** |
| **Whitespace Lost Dropped**| N/A | **1,047 dropped** | N/A | **50 dropped** |
| **Duplicates Dropped** | N/A | **125 dropped** | N/A | **13 dropped** |
| **Dataset Loader Valid** | Yes | **100% Validated** | Yes | **100% Validated** |

---

## 6. Training Pipeline Improvements

### 1. Response-Only Loss Masking
In [`training/llm_trainer.py`](file:///c:/Ganesh_149/uniguru/bhiv-uniguru/training/llm_trainer.py), Unsloth's native completion collator has been integrated:
```python
from unsloth.chat_templates import train_on_responses_only

trainer = train_on_responses_only(
    trainer,
    instruction_part="### Question:\n",
    response_part="### Answer:\n",
)
```
* **Effect**: All prompt tokens prior to `### Answer:\n` (System prompt, Context, and Question) are set to label `-100`.
* **Benefit**: Cross-entropy loss is computed **strictly on the answer tokens**. The model is no longer penalized for predicting context Wikipedia text, speeding up training and directly reinforcing correct answers and abstentions.

### 2. Prompt Template Standardization
In [`training/dataset_formatter.py`](file:///c:/Ganesh_149/uniguru/bhiv-uniguru/training/dataset_formatter.py):
The system instruction has been updated to explicitly cite the Marathi abstention target:
```
### System:
You are a helpful assistant. You must answer the user's question using ONLY the provided text context. If the answer is not in the context, say "दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही.".

### Context:
{context}

### Question:
{question}

### Answer:
{answer}
```

---

## 7. Checkpoint Preservation & Viability Assessment

### Existing Checkpoints Preserved
All existing checkpoints in `checkpoints/qwen2.5-7b-indic-squad-mr-full` remain untouched:
* `checkpoint-500` (Step 500)
* `checkpoint-750` (Step 750)
* `checkpoint-1000` (Step 1,000 — 161 MB adapter weights)

### Viability of Continuing Fine-Tuning vs. Fresh Training

| Factor | Option A: Continued Fine-Tuning from `checkpoint-1000` | Option B: Fresh Fine-Tuning from Base Qwen 2.5 7B |
|---|---|---|
| **Starting Point** | `checkpoints/.../checkpoint-1000` | `unsloth/Qwen2.5-7B-Instruct-bnb-4bit` |
| **Marathi Language Adaptation**| **Retained**: Model already understands Marathi subwords and vocabulary. | Must re-adapt over the initial 250–500 steps. |
| **Abstention Injection** | Agile: 250–500 steps with response masking will rapidly learn abstention. | Clean: Learns answerable and unanswerable balance from step 0. |
| **Risk of Prior Bias** | Low: LoRA rank 16 updates adapt quickly under response masking. | Zero prior bias. |
| **Recommended Learning Rate** | **`1e-4`** (slightly lower to preserve prior learning) | **`2e-4`** (standard fine-tuning schedule) |
| **Verdict** | **Recommended for fast iteration (2–3 hours)** | **Recommended for gold-standard benchmark** |

---

## 8. Ready-to-Execute PowerShell Commands

### Option A: Continued Fine-Tuning from `checkpoint-1000` (Fast Abstention Alignment)

```powershell
.\venv\Scripts\python.exe training\llm_trainer.py `
  --dataset data\training\indic_squad_mr_train_remediated.jsonl `
  --val-dataset data\validation\indic_squad_mr_val_remediated.jsonl `
  --epochs 1 `
  --batch-size 2 `
  --max-seq-length 1280 `
  --save-steps 250 `
  --max-steps 2000 `
  --learning-rate 0.0001 `
  --resume-from-checkpoint checkpoints\qwen2.5-7b-indic-squad-mr-full\checkpoint-1000 `
  --output-dir checkpoints\qwen2.5-7b-indic-squad-mr-remediated `
  --adapter-dir models\adapters\qwen2.5-7b-indic-squad-mr-remediated
```

### Option B: Fresh Fine-Tuning on Remediated Dataset (Gold Standard)

```powershell
.\venv\Scripts\python.exe training\llm_trainer.py `
  --dataset data\training\indic_squad_mr_train_remediated.jsonl `
  --val-dataset data\validation\indic_squad_mr_val_remediated.jsonl `
  --epochs 1 `
  --batch-size 2 `
  --max-seq-length 1280 `
  --save-steps 250 `
  --max-steps 2500 `
  --learning-rate 0.0002 `
  --output-dir checkpoints\qwen2.5-7b-indic-squad-mr-fresh `
  --adapter-dir models\adapters\qwen2.5-7b-indic-squad-mr-fresh
```

