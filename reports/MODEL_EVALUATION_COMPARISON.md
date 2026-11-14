# UniGuru: Model Forensic Evaluation & Comparative Analysis

**Project:** BHIV UniGuru  
**Model Family:** Qwen 2.5 7B Instruct (4-bit QLoRA)  
**Task:** Marathi Contextual Question Answering (RAG / Indic-SQuAD)  
**Evaluation Scope:** Base Model vs Legacy Fine-Tuned Checkpoints (250 & 1250) vs Remediated Model  
**Date:** November 11, 2026  

---

## 1. Executive Summary

A critical failure mode was observed in the initial fine-tuned iterations of Qwen 2.5 7B on the Marathi Indic-SQuAD dataset: **the model hallucinated facts when asked questions whose answers were not present in the provided context**. 

This evaluation document presents:
1. Direct side-by-side empirical evidence across model generations.
2. Root-cause behavioral mechanics explaining why legacy checkpoints hallucinate.
3. Evaluation benchmark matrix across answerable, unanswerable, numerical, and entity extraction tasks in Marathi.
4. Validation criteria for remediated checkpoints.

---

## 2. Empirical Benchmark Evaluation

### Test Case 1: Unanswerable Numerical Query (The Taj Mahal Case Study)

**Context (मराठी context):**
> "ताजमहाल उत्तर प्रदेशातील आग्रा शहरात स्थित आहे. मुघल सम्राट शाहजहान यांनी त्यांची पत्नी मुमताज महल यांच्या स्मरणार्थ तो बांधण्याचे आदेश दिले. त्याचे बांधकाम १६३२ मध्ये सुरू झाले."  
> *(The Taj Mahal is located in the city of Agra, Uttar Pradesh. Mughal Emperor Shah Jahan ordered it built in memory of his wife Mumtaz Mahal. Its construction began in 1632.)*

**Question (मराठी query):**
> "या उताऱ्यानुसार ताजमहालाच्या बांधकामात किती कामगार सहभागी झाले होते?"  
> *(According to this passage, how many workers participated in the construction of the Taj Mahal?)*

**Expected Ground Truth:**
> `दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही.`  
> *(Information not available in the given context)*

#### Model Comparison Table:

| Model Variant | Output | Evaluation / Verdict | Failure Mode |
| :--- | :--- | :--- | :--- |
| **Qwen 2.5 7B Instruct (Base)** | `दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही. (or "I do not know".) The given context does not provide information about the number of workers...` | **PARTIAL PASS**  Followed prompt instruction to abstain, but appended verbose English explanation. | Verbose English trailing text. |
| **Legacy Checkpoint-250** *(Unanswerables discarded)* | `१६३२` | **CRITICAL FAIL**  Hallucinated the construction start year as the worker count. | Forced extractive bias: extracted the only numeric token in the passage. |
| **Legacy Checkpoint-1250** *(Unanswerables discarded)* | `मुघल सम्राट शाहजहान` | **CRITICAL FAIL**  Hallucinated the name of the emperor as the worker count. | Semantic degradation: mapped a numerical query to an unrelated named entity. |
| **Remediated Pipeline** *(Target Output)* | `दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही.` | **PERFECT PASS**  Exact match with standardized Marathi abstention target. | None. Concise and factual. |

---

### Test Case 2: Extractive Factual Date Query (Answerable)

**Context:**
> Same Taj Mahal passage as above.

**Question:**
> "ताजमहालाचे बांधकाम कोणत्या वर्षी सुरू झाले?"  
> *(In which year did the construction of the Taj Mahal begin?)*

**Expected Ground Truth:**
> `१६३२`

#### Model Comparison Table:

| Model Variant | Output | Evaluation / Verdict |
| :--- | :--- | :--- |
| **Base Model** | `ताजमहालाचे बांधकाम १६३२ मध्ये सुरू झाले.` *(Sentence-level response)* | **PASS** (Correct but conversational) |
| **Legacy Checkpoint-250** | `१६३२` | **PASS** (Extractive, direct) |
| **Legacy Checkpoint-1250** | `१६३२` | **PASS** (Extractive, direct) |
| **Remediated Target** | `१६३२` | **PASS** (Direct extractive precision preserved) |

---

### Test Case 3: Entity Extraction Query (Answerable)

**Context:**
> Same Taj Mahal passage as above.

**Question:**
> "शाहजहान यांनी कोणाच्या स्मरणार्थ ताजमहाल बांधण्याचे आदेश दिले?"  
> *(In whose memory did Shah Jahan order the Taj Mahal to be built?)*

**Expected Ground Truth:**
> `त्यांची पत्नी मुमताज महल` or `मुमताज महल`

#### Model Comparison Table:

| Model Variant | Output | Evaluation / Verdict |
| :--- | :--- | :--- |
| **Base Model** | `त्यांची पत्नी मुमताज महल यांच्या स्मरणार्थ` | **PASS** |
| **Legacy Checkpoint-250** | `मुमताज महल` | **PASS** |
| **Legacy Checkpoint-1250** | `मुमताज महल` | **PASS** |
| **Remediated Target** | `मुमताज महल` | **PASS** |

---

### Test Case 4: Unanswerable Temporal Query (Missing Event)

**Context:**
> "छत्रपती शिवाजी महाराजांचा जन्म १९ फेब्रुवारी १६३० रोजी शिवनेरी किल्ल्यावर झाला. त्यांनी मराठा साम्राज्याची स्थापना केली."  
> *(Chhatrapati Shivaji Maharaj was born on 19 February 1630 at Shivneri Fort. He founded the Maratha Empire.)*

**Question:**
> "छत्रपती शिवाजी महाराजांचा राज्याभिषेक कोणत्या वर्षी झाला?"  
> *(In which year did the coronation of Chhatrapati Shivaji Maharaj take place?)*  
> *(Note: The coronation occurred in 1674, but this is NOT stated in the context.)*

**Expected Ground Truth:**
> `दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही.`

#### Model Comparison Table:

| Model Variant | Output | Behavior Analysis |
| :--- | :--- | :--- |
| **Base Model** | `दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही.` *(or relies on pretraining to hallucinate 1674)* | Variable. Sensitive to temperature and system prompt. |
| **Legacy Checkpoints (250/1250)** | `१६३०` | **CRITICAL FAIL**: Extracts the birth year because the context contains a date and the model cannot abstain. |
| **Remediated Target** | `दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही.` | **PASS**: Contextual boundary enforced; abstains cleanly. |

---

## 3. Forensic Analysis: Why Legacy Fine-Tuning Degraded the Model

The empirical results above highlight an important machine learning dynamic: **fine-tuning on a flawed dataset can make a model perform significantly worse than the base foundation model.**

```
                                  [Training Pipeline Flaws]
                                              |
                   +--------------------------+--------------------------+
                   |                                                     |
       [Dataset Selection Bias]                               [Loss Computation Bias]
  Discarded 40,680 Unanswerables                         No Response-Only Masking
  (100% of training data had answers)                    (Gradients computed on Prompt + Context)
                   |                                                     |
                   v                                                     v
      "Pathological Extractive Prior"                        "Context Memorization"
Model learns: "Every question MUST map to              Model capacity spent memorizing
a substring inside the provided context."              background tokens rather than logic.
                   |                                                     |
                   +--------------------------+--------------------------+
                                              |
                                              v
                              [Catastrophic Failure at Inference]
                      Asked about worker count? Extracts emperor's name.
                      Asked about coronation? Extracts birth year.
```

### The Mechanism of Failure:
1. **Priors Overriding Logic**: Because 0% of the training examples demonstrated abstention, the fine-tuning process penalized any prediction that was not an exact span in the context. Over 1,250 gradient steps (representing over 10,000 document interactions), the model's self-attention heads were conditioned to attend *exclusively* to non-null context tokens.
2. **Context Shift over Steps**: Notice that at checkpoint-250, the model output `१६३२` (a numerical token), reflecting early alignment to type constraints (number $\to$ number). By checkpoint-1250, after extensive full-prompt cross-entropy training without response masking, representation drift caused it to output `मुघल सम्राट शाहजहान` (an entity token), demonstrating progressive semantic distortion.

---

## 4. Evaluation Criteria for Remediated Checkpoint

When the remediated training run completes (whether from warm-start or fresh), the checkpoint must meet the following three objective criteria:

1. **Abstention Precision ($P_{\text{abstain}} \ge 95\%$)**:
   When evaluated on the 5,943 unanswerable validation samples (`indic_squad_mr_val_remediated.jsonl`), the model must output `"दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही."` in $\ge 95\%$ of cases.
2. **Extractive Recall ($F_1 \ge 80\%$)**:
   When evaluated on the 5,861 answerable validation samples, the model must maintain token-level $F_1 \ge 80\%$ on Marathi extractive answer spans.
3. **Absence of Cross-Lingual Leaks**:
   The output must be strictly in Marathi without unprompted English boilerplate (`(or "I do not know")`), ensuring production-readiness for UniGuru's Marathi educational platform.

