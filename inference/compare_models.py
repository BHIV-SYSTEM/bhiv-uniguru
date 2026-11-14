"""
Compare Original Base Model vs Fine-Tuned Model Side-by-Side.
Uses PEFT's disable_adapter() to run both through the same 12GB VRAM footprint.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from training.dataset_formatter import format_rag_inference_prompt
from training.training_utils import release_cuda_memory


class ModelComparator:
    def __init__(self, adapter_path: str | Path, max_seq_length: int = 1536):
        p = Path(adapter_path)
        if not p.is_absolute():
            p = _PROJECT_ROOT / p

        # Auto-detect latest checkpoint if specific checkpoint was rotated or parent folder passed
        if not (p / "adapter_config.json").exists():
            search_dir = p.parent if "checkpoint-" in p.name else p
            if search_dir.exists():
                cps = [
                    d for d in search_dir.glob("checkpoint-*")
                    if (d / "adapter_config.json").exists()
                ]
                if cps:
                    def _step(d):
                        try:
                            return int(d.name.split("-")[-1])
                        except Exception:
                            return 0
                    latest = sorted(cps, key=_step)[-1]
                    print(f"[INFO] Target checkpoint '{p.name}' not found. Auto-selected latest: {latest.name}")
                    p = latest

        if not (p / "adapter_config.json").exists():
            raise FileNotFoundError(
                f"No valid adapter checkpoint found at: {p.resolve()}\n"
                "Please verify that at least one checkpoint directory exists with 'adapter_config.json'."
            )

        self.adapter_path = p
        self.max_seq_length = max_seq_length
        self.model = None
        self.tokenizer = None

    def load(self):
        import torch
        from unsloth import FastLanguageModel

        print(f"\n[INFO] Loading base model + adapter from: {self.adapter_path.resolve()}...")
        self.model, self.tokenizer = FastLanguageModel.from_pretrained(
            model_name=str(self.adapter_path),
            max_seq_length=self.max_seq_length,
            dtype=None,
            load_in_4bit=True,
        )
        FastLanguageModel.for_inference(self.model)
        print("[INFO] Model loaded successfully. Ready for comparison!\n")

    def _generate_text(self, prompt: str, temperature: float = 0.3, max_new_tokens: int = 256) -> str:
        import torch

        inputs = self.tokenizer([prompt], return_tensors="pt").to("cuda")
        input_len = inputs["input_ids"].shape[1]

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=(temperature > 0.0),
                use_cache=True,
            )
        generated = outputs[0][input_len:]
        return self.tokenizer.decode(generated, skip_special_tokens=True).strip()

    def compare(self, context: str, question: str) -> dict[str, str]:
        prompt = format_rag_inference_prompt(context=context, question=question)

        # 1. Answer with Fine-Tuned Adapter
        finetuned_ans = self._generate_text(prompt)

        # 2. Answer with Original Base Model (Adapter Disabled)
        with self.model.disable_adapter():
            original_ans = self._generate_text(prompt)

        return {
            "original_base": original_ans,
            "fine_tuned": finetuned_ans,
        }

    def close(self):
        self.model = None
        self.tokenizer = None
        release_cuda_memory()


def main():
    parser = argparse.ArgumentParser(description="Side-by-Side Model Comparison (Base vs Fine-Tuned)")
    parser.add_argument(
        "--adapter-dir",
        type=str,
        default="checkpoints/qwen2.5-7b-indic-squad-mr-full/checkpoint-250",
        help="Path to fine-tuned LoRA checkpoint/adapter",
    )
    parser.add_argument("--context", type=str, default=None, help="Marathi Context")
    parser.add_argument("--question", type=str, default=None, help="Marathi Question")
    parser.add_argument("--interactive", action="store_true", help="Launch interactive comparison shell")
    args = parser.parse_args()

    comparator = ModelComparator(adapter_path=args.adapter_dir)
    comparator.load()

    try:
        if args.context and args.question:
            res = comparator.compare(args.context, args.question)
            print("=" * 60)
            print(f"QUESTION: {args.question}")
            print("-" * 60)
            print(f"1. ORIGINAL BASE MODEL:\n{res['original_base']}")
            print("-" * 60)
            print(f"2. FINE-TUNED (CHECKPOINT 250):\n{res['fine_tuned']}")
            print("=" * 60)
            return

        if args.interactive:
            print("=== Interactive Comparison Mode (Type 'exit' or 'quit' to stop) ===")
            while True:
                ctx = input("\nEnter Context: ").strip()
                if ctx.lower() in ("exit", "quit"):
                    break
                q = input("Enter Question: ").strip()
                if q.lower() in ("exit", "quit"):
                    break

                res = comparator.compare(ctx, q)
                print("\n" + "=" * 60)
                print(f"[ORIGINAL BASE MODEL]:\n{res['original_base']}")
                print("-" * 60)
                print(f"[FINE-TUNED MODEL (CP 250)]:\n{res['fine_tuned']}")
                print("=" * 60)
        else:
            print("Please pass --context and --question, or use --interactive.")
    finally:
        comparator.close()


if __name__ == "__main__":
    main()

