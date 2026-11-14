"""
UniGuru Fine-Tuned Qwen 2.5 Inference Engine.
Loads 4-bit base model with the fine-tuned LoRA adapter for grounded RAG QA.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from training.dataset_formatter import format_rag_inference_prompt
from training.training_utils import get_environment_info, release_cuda_memory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("uniguru.inference")


class RAGInferenceEngine:
    """
    Inference manager that loads a 4-bit Qwen base model + fine-tuned LoRA adapter.
    """

    def __init__(
        self,
        adapter_path: Optional[str | Path] = None,
        base_model_name: Optional[str] = None,
        config_path: Optional[str | Path] = None,
        max_seq_length: int = 2048,
    ):
        self.config = self._load_config(config_path)
        
        cfg_paths = self.config.get("paths", {})
        default_adapter = _PROJECT_ROOT / cfg_paths.get("adapter_dir", "models/adapters/qwen2.5-7b-rag-adapter")
        self.adapter_path = Path(adapter_path) if adapter_path else default_adapter
        if not self.adapter_path.is_absolute():
            self.adapter_path = _PROJECT_ROOT / self.adapter_path

        self.base_model_name = (
            base_model_name
            or self.config.get("model", {}).get("name_or_path", "unsloth/Qwen2.5-7B-Instruct-bnb-4bit")
        )
        self.max_seq_length = max_seq_length
        self.model = None
        self.tokenizer = None
        self.loaded = False

    @staticmethod
    def _load_config(config_path: Optional[str | Path]) -> Dict[str, Any]:
        default_cfg = _PROJECT_ROOT / "config" / "llm_training.yaml"
        p = Path(config_path) if config_path else default_cfg
        if p.is_file():
            with p.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def load_model(self) -> None:
        """Load the 4-bit base model and apply the trained LoRA adapter weights."""
        if self.loaded:
            return

        env = get_environment_info()
        if not env["cuda_available"]:
            raise RuntimeError(
                "CUDA GPU is required to load 4-bit Qwen 2.5 7B model for inference. "
                "Development machine does not have a compatible GPU."
            )

        if not self.adapter_path.exists():
            raise FileNotFoundError(
                f"Trained adapter not found at {self.adapter_path.resolve()}. "
                "Please run `python training/llm_trainer.py` to train the adapter first."
            )

        try:
            from unsloth import FastLanguageModel
        except ImportError as exc:
            raise ImportError(
                "Unsloth is required for inference. Install via `setup_env.bat` or `setup_env_wsl.sh`."
            ) from exc

        logger.info(f"Loading fine-tuned LoRA adapter from: {self.adapter_path.resolve()}")
        self.model, self.tokenizer = FastLanguageModel.from_pretrained(
            model_name=str(self.adapter_path),
            max_seq_length=self.max_seq_length,
            dtype=None,
            load_in_4bit=True,
        )
        FastLanguageModel.for_inference(self.model)
        self.loaded = True
        logger.info("Fine-tuned model and tokenizer loaded and optimized for inference.")

    def generate(
        self,
        context: str,
        question: str,
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        repetition_penalty: Optional[float] = None,
    ) -> str:
        """
        Generate grounded answer using context and question.
        """
        if not context or not context.strip():
            return "I do not know (context was not provided)."

        if not question or not question.strip():
            return "Please provide a valid question."

        if not self.loaded:
            self.load_model()

        import torch

        prompt = format_rag_inference_prompt(context=context, question=question)
        inputs = self.tokenizer([prompt], return_tensors="pt").to("cuda")

        inf_cfg = self.config.get("inference", {})
        gen_tokens = max_new_tokens or int(inf_cfg.get("max_new_tokens", 512))
        temp = temperature if temperature is not None else float(inf_cfg.get("temperature", 0.3))
        top_p_val = top_p if top_p is not None else float(inf_cfg.get("top_p", 0.9))
        rep_pen = repetition_penalty or float(inf_cfg.get("repetition_penalty", 1.1))

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=gen_tokens,
                temperature=temp,
                top_p=top_p_val,
                repetition_penalty=rep_pen,
                do_sample=(temp > 0.0),
                use_cache=True,
            )

        # Decode answer tokens only (slice past the prompt input)
        input_len = inputs["input_ids"].shape[1]
        generated_tokens = outputs[0][input_len:]
        answer = self.tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
        return answer

    def close(self) -> None:
        """Release model weights and GPU memory."""
        self.model = None
        self.tokenizer = None
        self.loaded = False
        release_cuda_memory()
        logger.info("Released inference model and cleared GPU memory.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="UniGuru Fine-Tuned Qwen 2.5 Inference")
    parser.add_argument("--adapter-dir", type=str, default=None, help="Path to LoRA adapter folder")
    parser.add_argument("--context", type=str, default=None, help="Context string to answer from")
    parser.add_argument("--question", type=str, default=None, help="User question")
    parser.add_argument("--interactive", action="store_true", help="Launch interactive CLI query loop")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine = RAGInferenceEngine(adapter_path=args.adapter_dir)

    env = get_environment_info()
    if not env["cuda_available"]:
        print("\n" + "=" * 70)
        print(" [INFO] UniGuru Inference Engine Ready.")
        print(f" Development Machine detected: {env.get('python_version', '').split()[0]} on {sys.platform}")
        print(" A compatible CUDA GPU (RTX 3060 12GB) is required to load 4-bit weights.")
        print(" To run inference on your training machine:")
        print(f"   python inference/llm_inference.py --context '...' --question '...'")
        print("=" * 70 + "\n")
        return

    if not engine.adapter_path.exists():
        print(f"\n[ERROR] Adapter not found at: {engine.adapter_path.resolve()}")
        print("Train the model first using: python training/llm_trainer.py\n")
        return

    try:
        engine.load_model()
    except Exception as exc:
        logger.error(f"Failed to load model: {exc}")
        return

    if args.context and args.question:
        answer = engine.generate(context=args.context, question=args.question)
        print("\n=== ANSWER ===")
        print(answer)
        print("==============\n")
        engine.close()
        return

    if args.interactive:
        print("\n--- UniGuru Grounded RAG Inference Loop (Type 'exit' to quit) ---")
        try:
            while True:
                ctx = input("\nEnter Context: ").strip()
                if ctx.lower() in ("exit", "quit"):
                    break
                q = input("Enter Question: ").strip()
                if q.lower() in ("exit", "quit"):
                    break
                ans = engine.generate(context=ctx, question=q)
                print(f"\nAnswer: {ans}")
        finally:
            engine.close()
    else:
        print("Please provide --context and --question, or use --interactive.")


if __name__ == "__main__":
    main()

