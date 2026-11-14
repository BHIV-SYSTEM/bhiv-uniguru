# UniGuru Qwen 2.5 7B Instruct — Marathi Indic-SQuAD (Fine-Tuned Model Guide)

This guide documents how to access, download, evaluate, and deploy the fine-tuned **Qwen 2.5 7B Instruct** Marathi RAG model trained for **BHIV UniGuru**.

---

## 1. Model Availability & Hub Access

The model is published on Hugging Face Hub:
* **Hugging Face Repository**: [https://huggingface.co/csshivamverma54/qwen2.5-7b-marathi-indic-squad](https://huggingface.co/csshivamverma54/qwen2.5-7b-marathi-indic-squad)
* **Local Checkpoint Path**: `models/adapters/qwen2.5-7b-indic-squad-mr-remediated/`
* **Base Architecture**: `unsloth/Qwen2.5-7B-Instruct-bnb-4bit` (4-bit NF4 Quantization)
* **LoRA Configuration**: Rank $r=16$, Alpha $\alpha=16$, Target Modules: `q, k, v, o, gate, up, down`
* **Training Iterations**: 3,000 steps (~24,000 samples, final response-only loss $\approx 0.02 - 0.05$)

---

## 2. Quickstart: Inference in Python

### Method A: Direct from Hugging Face Hub (Recommended)

You can load and run inference on any machine with an NVIDIA GPU (requires $\ge 6$ GB VRAM for 4-bit inference):

```python
import torch
from unsloth import FastLanguageModel

# 1. Load model directly from Hugging Face Hub
model_id = "csshivamverma54/qwen2.5-7b-marathi-indic-squad"
max_seq_length = 1536

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=model_id,
    max_seq_length=max_seq_length,
    dtype=None,          # Auto-detects float16/bfloat16
    load_in_4bit=True,   # Fits in ~4.5 GB VRAM
)
FastLanguageModel.for_inference(model)

# 2. Format your prompt with Context and Question
context = """ताजमहाल उत्तर प्रदेशातील आग्रा शहरात स्थित आहे. मुघल सम्राट शाहजहान यांनी त्यांची पत्नी मुमताज महल यांच्या स्मरणार्थ तो बांधण्याचे आदेश दिले. त्याचे बांधकाम १६३२ मध्ये सुरू झाले."""
question = "या उताऱ्यानुसार ताजमहालाच्या बांधकामात किती कामगार सहभागी झाले होते?"

prompt = f"""### System:
You are a helpful assistant. You must answer the user's question using ONLY the provided text context. If the answer is not in the context, say "दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही." (or "I do not know").

### Context:
{context}

### Question:
{question}

### Answer:
"""

# 3. Generate response
inputs = tokenizer([prompt], return_tensors="pt").to("cuda")
with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=64,
        temperature=0.1,
        use_cache=True,
    )

answer = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
print("Model Output:", answer)
# Expected Output: दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही.
```

---

### Method B: Using Local CLI Comparator

If running from the local repository, you can evaluate the fine-tuned adapter side-by-side with the base model using:

```powershell
cd C:\Ganesh_149\uniguru\bhiv-uniguru

# Test unanswerable question (verifies abstention without hallucination)
.\venv\Scripts\python.exe inference\compare_models.py `
  --adapter-dir models\adapters\qwen2.5-7b-indic-squad-mr-remediated `
  --context "ताजमहाल उत्तर प्रदेशातील आग्रा शहरात स्थित आहे. मुघल सम्राट शाहजहान यांनी त्यांची पत्नी मुमताज महल यांच्या स्मरणार्थ तो बांधण्याचे आदेश दिले. त्याचे बांधकाम १६३२ मध्ये सुरू झाले." `
  --question "या उताऱ्यानुसार ताजमहालाच्या बांधकामात किती कामगार सहभागी झाले होते?"

# Test answerable factual query
.\venv\Scripts\python.exe inference\compare_models.py `
  --adapter-dir models\adapters\qwen2.5-7b-indic-squad-mr-remediated `
  --context "ताजमहाल उत्तर प्रदेशातील आग्रा शहरात स्थित आहे. मुघल सम्राट शाहजहान यांनी त्यांची पत्नी मुमताज महल यांच्या स्मरणार्थ तो बांधण्याचे आदेश दिले. त्याचे बांधकाम १६३२ मध्ये सुरू झाले." `
  --question "ताजमहालाचे बांधकाम कोणत्या वर्षी सुरू झाले?"
```

---

## 3. Standard Prompt Format

The model was trained strictly on the following RAG prompt template:

```text
### System:
You are a helpful assistant. You must answer the user's question using ONLY the provided text context. If the answer is not in the context, say "दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही." (or "I do not know").

### Context:
{context}

### Question:
{question}

### Answer:
{answer}<|im_end|>
```

---

## 4. Key Performance Highlights & Benchmark Results

### Case Study: Missing Workforce Query (Taj Mahal)
* **Query:** *"According to this passage, how many workers participated in the construction of the Taj Mahal?"* (Information absent from context).
* **Expected Output:** `"दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही."`

| Model Variant | Prediction | Verdict |
| :--- | :--- | :--- |
| **Qwen 2.5 7B Instruct (Base)** | Abstains but appends conversational English text | **Partial Pass** |
| **Legacy Checkpoint-250** *(Unanswerables discarded)* | `१६३२` *(Construction start year)* | **Critical Hallucination** |
| **Legacy Checkpoint-1250** *(Unanswerables discarded)* | `मुघल सम्राट शाहजहान` *(Emperor's name)* | **Critical Hallucination** |
| **Remediated Checkpoint-3000 (Current)** | `दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही.` | **Exact Match / 100% Pass** |

---

## 5. Technical Pipeline Improvements

1. **Remediated Indic-SQuAD Dataset:**  
   Recovered 39,606 genuine Stanford SQuAD 2.0 unanswerables (33.77% of training data) that were previously discarded due to empty answer arrays, teaching the model strict contextual abstention boundaries.
2. **Response-Only Loss Masking:**  
   Applied native Unsloth `train_on_responses_only`, masking prompt tokens with `-100` so parameter updates focus 100% on factual answer tokens rather than memorizing passage backgrounds.
3. **Warm-Start Continuity:**  
   Preserved and stabilized weights across multiple training runs from step 1 through 3,000 without learning rate spikes or catastrophic forgetting.
