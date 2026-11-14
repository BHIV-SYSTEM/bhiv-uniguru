"""
UniGuru Local Fine-Tuned LLM Microservice
Serves the fine-tuned Qwen 2.5 7B Marathi model locally on port 8001 for seamless integration with UniGuru Backend RAG and Frontend.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import uvicorn

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from training.dataset_formatter import format_rag_inference_prompt
from training.training_utils import release_cuda_memory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("uniguru.llm_service")

app = FastAPI(title="UniGuru Local LLM Service", description="Local Qwen 2.5 7B Fine-Tuned Marathi Inference API")

# Global model and tokenizer
_MODEL = None
_TOKENIZER = None


class GenerateRequest(BaseModel):
    query: Optional[str] = None
    prompt: Optional[str] = None
    context: Optional[str] = None
    messages: Optional[List[Dict[str, str]]] = None
    max_new_tokens: int = 128
    temperature: float = 0.1


def load_model(model_name_or_path: str, max_seq_length: int = 1536):
    global _MODEL, _TOKENIZER
    import torch
    from unsloth import FastLanguageModel

    logger.info(f"Loading model/adapter from: {model_name_or_path}...")
    _MODEL, _TOKENIZER = FastLanguageModel.from_pretrained(
        model_name=model_name_or_path,
        max_seq_length=max_seq_length,
        dtype=None,
        load_in_4bit=True,
    )
    FastLanguageModel.for_inference(_MODEL)
    logger.info("Model loaded successfully into GPU memory! Ready for requests.")


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _MODEL is not None}


@app.post("/generate")
@app.post("/api/generate")
@app.post("/chat/completions")
def generate(req: GenerateRequest):
    global _MODEL, _TOKENIZER
    if _MODEL is None or _TOKENIZER is None:
        raise HTTPException(status_code=503, detail="Model is not loaded.")

    import torch

    # Extract user question from query, prompt, or messages list
    user_query = req.query or req.prompt
    if not user_query and req.messages:
        for m in reversed(req.messages):
            if m.get("role") == "user":
                user_query = m.get("content")
                break
    user_query = str(user_query or "").strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Query or prompt is required.")

    # If context was provided separately, use the official Devanagari RAG prompt template
    if req.context:
        formatted_prompt = format_rag_inference_prompt(context=req.context, question=user_query)
    else:
        # Check if the prompt is already formatted
        if "### System:" in user_query:
            formatted_prompt = user_query
        else:
            formatted_prompt = f"### System:\nYou are a helpful assistant with a strong command of Marathi and English. Answer concisely.\n\n### Question:\n{user_query}\n\n### Answer:\n"

    inputs = _TOKENIZER([formatted_prompt], return_tensors="pt").to("cuda")
    input_len = inputs["input_ids"].shape[1]

    with torch.no_grad():
        outputs = _MODEL.generate(
            **inputs,
            max_new_tokens=req.max_new_tokens,
            temperature=req.temperature,
            do_sample=(req.temperature > 0.0),
            use_cache=True,
        )

    generated = outputs[0][input_len:]
    answer = _TOKENIZER.decode(generated, skip_special_tokens=True).strip()

    return {
        "answer": answer,
        "response": answer,
        "output": answer,
        "model": "qwen2.5-7b-marathi-indic-squad",
    }


def main():
    parser = argparse.ArgumentParser(description="UniGuru Local Fine-Tuned Model Server")
    parser.add_argument(
        "--model",
        type=str,
        default="models/adapters/qwen2.5-7b-indic-squad-mr-remediated",
        help="Path to local adapter directory or Hugging Face Hub ID (e.g. csshivamverma54/qwen2.5-7b-marathi-indic-squad)",
    )
    parser.add_argument("--port", type=int, default=8001, help="Port to run LLM microservice on")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface to bind")
    args = parser.parse_args()

    model_target = args.model
    # If local path does not exist, fall back to Hugging Face Hub repo
    p = Path(model_target)
    if not p.is_absolute():
        p = _PROJECT_ROOT / p
    if not p.exists():
        logger.info(f"Local path {p} not found; falling back to Hugging Face Hub: csshivamverma54/qwen2.5-7b-marathi-indic-squad")
        model_target = "csshivamverma54/qwen2.5-7b-marathi-indic-squad"
    else:
        model_target = str(p)

    load_model(model_name_or_path=model_target)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

