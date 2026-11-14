"""
UniGuru Local Fine-Tuned LLM Microservice
Serves the fine-tuned Qwen 2.5 7B Marathi model locally on port 8001 for seamless integration with UniGuru Backend RAG and Frontend.
Supports multilingual inference:
  - English questions -> English responses with complete code & explanations
  - Marathi questions -> Marathi responses
  - Explicit language overrides
  - Grounded RAG with strict abstention in the requested language
"""
from __future__ import annotations

import argparse
import logging
import os
import re
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

app = FastAPI(title="UniGuru Local LLM Service", description="Local Qwen 2.5 7B Multilingual & Marathi Inference API")

# Global model and tokenizer
_MODEL = None
_TOKENIZER = None


class GenerateRequest(BaseModel):
    query: Optional[str] = None
    prompt: Optional[str] = None
    context: Optional[str] = None
    messages: Optional[List[Dict[str, str]]] = None
    language: Optional[str] = None
    max_new_tokens: int = 512
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

    # Determine requested language
    req_lang = (req.language or "").strip().lower()
    if not req_lang:
        devanagari_count = len(re.findall(r"[\u0900-\u097f]", user_query))
        latin_count = len(re.findall(r"[A-Za-z]", user_query))
        # Check for explicit override in text
        if re.search(r"(?:\b(?:in\s+english|to\s+english|in\s+en)\b|english\s*मध्ये|इंग्रजीत|इंग्रजी\s*मध्ये)", user_query, re.IGNORECASE):
            req_lang = "en"
        elif re.search(r"(?:\b(?:in\s+marathi|to\s+marathi|in\s+mr)\b|marathi\s*मध्ये|मराठीत|मराठी\s*मध्ये)", user_query, re.IGNORECASE):
            req_lang = "mr"
        elif devanagari_count and devanagari_count >= latin_count:
            req_lang = "mr"
        else:
            req_lang = "en"

    # 1. Grounded Context-Based RAG
    if req.context:
        if req_lang == "mr":
            formatted_prompt = format_rag_inference_prompt(context=req.context, question=user_query)
        else:
            formatted_prompt = (
                "### System:\n"
                "You are a helpful assistant. You must answer the user's question using ONLY the provided text context. "
                "If the answer is not in the context, say \"The provided context does not contain this information.\" (or \"I do not know\").\n\n"
                f"### Context:\n{req.context.strip()}\n\n"
                f"### Question:\n{user_query.strip()}\n\n"
                "### Answer:\n"
            )
    # 2. ChatML formatted input already provided
    elif "<|im_start|>" in user_query:
        formatted_prompt = user_query
    # 3. Explicit messages list provided (conversation router or standard chat)
    elif req.messages and len(req.messages) > 0:
        # Augment or ensure system message specifies response language
        has_system = False
        augmented_messages = []
        for m in req.messages:
            if m.get("role") == "system":
                has_system = True
                content = m.get("content", "")
                lang_rule = "Respond entirely in Marathi." if req_lang == "mr" else "Respond entirely in English."
                if lang_rule not in content:
                    content = f"{content} {lang_rule}"
                augmented_messages.append({"role": "system", "content": content})
            else:
                augmented_messages.append(m)
        if not has_system:
            lang_rule = "Respond entirely in Marathi." if req_lang == "mr" else "Respond entirely in English."
            augmented_messages.insert(0, {
                "role": "system",
                "content": f"You are UniGuru, a helpful educational AI assistant. {lang_rule} Provide clear, working code and detailed explanations where helpful."
            })
        formatted_prompt = _TOKENIZER.apply_chat_template(
            augmented_messages, tokenize=False, add_generation_prompt=True
        )
    # 4. General conversational prompt (use native ChatML template for Qwen 2.5)
    else:
        lang_rule = "Respond entirely in Marathi." if req_lang == "mr" else "Respond entirely in English."
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are UniGuru, a helpful and knowledgeable educational AI assistant. {lang_rule} "
                    "Explain concepts clearly, and provide complete, working code and examples whenever requested. "
                    "Do not require documents or knowledge-base citations for general questions."
                ),
            },
            {"role": "user", "content": user_query},
        ]
        formatted_prompt = _TOKENIZER.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

    inputs = _TOKENIZER([formatted_prompt], return_tensors="pt").to("cuda")
    input_len = inputs["input_ids"].shape[1]

    with torch.no_grad():
        outputs = _MODEL.generate(
            **inputs,
            max_new_tokens=max(req.max_new_tokens, 256),
            temperature=max(req.temperature, 0.05),
            do_sample=(req.temperature > 0.05),
            repetition_penalty=1.05,
            use_cache=True,
        )

    generated = outputs[0][input_len:]
    answer = _TOKENIZER.decode(generated, skip_special_tokens=True).strip()

    return {
        "answer": answer,
        "response": answer,
        "output": answer,
        "model": "qwen2.5-7b-marathi-indic-squad",
        "language": req_lang,
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

    # Priority: 1. Local path if exists, 2. Hugging Face Hub ID
    target_model = args.model
    if not os.path.isdir(target_model):
        logger.info(f"Local path '{target_model}' not found. Falling back to Hugging Face Hub model: csshivamverma54/qwen2.5-7b-marathi-indic-squad")
        target_model = "csshivamverma54/qwen2.5-7b-marathi-indic-squad"

    load_model(target_model)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
