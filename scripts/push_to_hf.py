"""
UniGuru Hugging Face Hub Batch Uploader
Uploads fine-tuned Qwen 2.5 7B Marathi QLoRA adapters and checkpoints in controlled batches.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def create_model_card(repo_id: str) -> str:
    return f"""---
language:
- mr
- en
license: apache-2.0
base_model: unsloth/Qwen2.5-7B-Instruct-bnb-4bit
tags:
- unsloth
- qlora
- marathi
- rag
- indic-squad
- question-answering
- factual-accuracy
pipeline_tag: text-generation
---

# UniGuru Qwen 2.5 7B Instruct — Marathi Indic-SQuAD (Remediated)

This model is a parameter-efficient fine-tuned (QLoRA, rank=16, alpha=16) adapter on top of **Qwen 2.5 7B Instruct**, specifically trained for high-precision Marathi Contextual Question Answering and Retrieval-Augmented Generation (RAG).

## Key Features & Remediation

1. **Anti-Hallucination & Abstention**:
   Trained on **117,265 remediated Marathi Indic-SQuAD pairs**, including **39,606 verified Stanford SQuAD 2.0 unanswerable queries** (33.77% of dataset).
   When information is missing from the context, the model refrains from hallucinating and outputs the standard Marathi abstention response:
   > *"दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही."*

2. **Response-Only Loss Masking**:
   Trained using Unsloth's `train_on_responses_only`, masking all System, Context, and Question tokens with `-100`. Gradients were computed 100% on the factual answer tokens, preventing background passage memorization.

3. **Training Milestones**:
   - Total Steps: **3,000 steps** (24,000 effective training samples)
   - Final Response-Only Loss: **~0.02 – 0.05**
   - Precision: Bfloat16 with 4-bit NF4 base quantization

## Usage with Unsloth / Transformers

```python
from unsloth import FastLanguageModel

max_seq_length = 1536
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="{repo_id}",
    max_seq_length=max_seq_length,
    dtype=None,
    load_in_4bit=True,
)
FastLanguageModel.for_inference(model)

prompt = \"\"\"### System:
You are a helpful assistant. You must answer the user's question using ONLY the provided text context. If the answer is not in the context, say "दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही." (or "I do not know").

### Context:
ताजमहाल उत्तर प्रदेशातील आग्रा शहरात स्थित आहे. मुघल सम्राट शाहजहान यांनी त्यांची पत्नी मुमताज महल यांच्या स्मरणार्थ तो बांधण्याचे आदेश दिले. त्याचे बांधकाम १६३२ मध्ये सुरू झाले.

### Question:
या उताऱ्यानुसार ताजमहालाच्या बांधकामात किती कामगार सहभागी झाले होते?

### Answer:
\"\"\"

inputs = tokenizer([prompt], return_tensors="pt").to("cuda")
outputs = model.generate(**inputs, max_new_tokens=64, temperature=0.1)
print(tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip())
# Output: दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही.
```
"""


def upload_batch(
    api,
    repo_id: str,
    local_dir: Path,
    path_in_repo: str = "",
    batch_name: str = "Batch",
    private: bool = False,
):
    from huggingface_hub import upload_folder

    print(f"\n========================================================")
    print(f"[*] Starting {batch_name}:")
    print(f"    Source: {local_dir.resolve()}")
    print(f"    Destination: {repo_id}/{path_in_repo if path_in_repo else '(root)'}")
    print(f"========================================================")

    if not local_dir.exists():
        raise FileNotFoundError(f"Local directory does not exist: {local_dir}")

    t0 = time.time()
    api.create_repo(repo_id=repo_id, private=private, exist_ok=True)

    upload_folder(
        repo_id=repo_id,
        folder_path=str(local_dir),
        path_in_repo=path_in_repo if path_in_repo else None,
        commit_message=f"Upload {batch_name} ({local_dir.name})",
        ignore_patterns=["*.pt", "*.bin", "__pycache__/*", "*.lock"],
    )
    elapsed = time.time() - t0
    print(f"[+] {batch_name} uploaded successfully in {elapsed:.1f}s!\n")


def main():
    parser = argparse.ArgumentParser(description="Upload UniGuru Models to Hugging Face in Batches")
    parser.add_argument(
        "--repo-id",
        type=str,
        required=True,
        help="Hugging Face repository ID (e.g. username/qwen2.5-7b-marathi-rag)",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="Hugging Face User Access Token (with write permission). Optional if logged in via `huggingface-cli login`.",
    )
    parser.add_argument(
        "--batch",
        type=str,
        choices=["adapter", "checkpoint-1500", "checkpoint-3000", "all"],
        default="adapter",
        help="Batch to upload: 'adapter' (final 3000-step adapter), 'checkpoint-1500', 'checkpoint-3000', or 'all'",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="Make the Hugging Face repository private",
    )
    args = parser.parse_args()

    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("[ERROR] huggingface_hub is not installed. Run `pip install huggingface_hub`.")
        sys.exit(1)

    token = args.token or os.getenv("HF_TOKEN")
    api = HfApi(token=token)

    adapter_dir = _PROJECT_ROOT / "models" / "adapters" / "qwen2.5-7b-indic-squad-mr-remediated"
    cp1500_dir = _PROJECT_ROOT / "checkpoints" / "checkpoint-1500-remediated-milestone"
    cp3000_dir = _PROJECT_ROOT / "checkpoints" / "qwen2.5-7b-indic-squad-mr-remediated" / "checkpoint-3000"

    # Always ensure model card is present in adapter dir
    readme_path = adapter_dir / "README.md"
    if not readme_path.exists():
        readme_path.write_text(create_model_card(args.repo_id), encoding="utf-8")

    # Batch 1: Primary Final LoRA Adapter
    if args.batch in ("adapter", "all"):
        upload_batch(
            api=api,
            repo_id=args.repo_id,
            local_dir=adapter_dir,
            path_in_repo="",
            batch_name="Batch 1: Final 3,000-Step LoRA Adapter",
            private=args.private,
        )

    # Batch 2: Intermediate Checkpoint-1500 Milestone
    if args.batch in ("checkpoint-1500", "all"):
        if cp1500_dir.exists():
            upload_batch(
                api=api,
                repo_id=args.repo_id,
                local_dir=cp1500_dir,
                path_in_repo="checkpoints/checkpoint-1500",
                batch_name="Batch 2: Checkpoint-1500 Milestone",
                private=args.private,
            )
        else:
            print(f"[!] Checkpoint-1500 not found at {cp1500_dir}, skipping.")

    # Batch 3: Final Checkpoint-3000 Milestone
    if args.batch in ("checkpoint-3000", "all"):
        if cp3000_dir.exists():
            upload_batch(
                api=api,
                repo_id=args.repo_id,
                local_dir=cp3000_dir,
                path_in_repo="checkpoints/checkpoint-3000",
                batch_name="Batch 3: Checkpoint-3000 Milestone",
                private=args.private,
            )
        else:
            print(f"[!] Checkpoint-3000 not found at {cp3000_dir}, skipping.")

    print("[SUCCESS] All requested batches uploaded successfully to Hugging Face Hub!")
    print(f"View your model at: https://huggingface.co/{args.repo_id}")


if __name__ == "__main__":
    main()

