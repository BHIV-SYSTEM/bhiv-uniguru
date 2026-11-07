"""
RAG Prompt Formatter for UniGuru LLM Fine-Tuning and Inference.
Formats records according to the canonical RAG instruction template.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Canonical UniGuru RAG instruction prompt template
RAG_PROMPT_TEMPLATE = """### System:
You are a helpful assistant. You must answer the user's question using ONLY the provided text context. If the answer is not in the context, say "I do not know".

### Context:
{context}

### Question:
{question}

### Answer:
{answer}"""

# Inference prompt (with open answer section)
RAG_INFERENCE_TEMPLATE = """### System:
You are a helpful assistant. You must answer the user's question using ONLY the provided text context. If the answer is not in the context, say "I do not know".

### Context:
{context}

### Question:
{question}

### Answer:
"""


def format_rag_record(record: Dict[str, str], eos_token: str = "") -> str:
    """
    Format a single (context, question, answer) record into training text.
    Appends eos_token if provided.
    """
    context = record.get("context", "").strip()
    question = record.get("question", "").strip()
    answer = record.get("answer", "").strip()

    prompt = RAG_PROMPT_TEMPLATE.format(
        context=context,
        question=question,
        answer=answer,
    )
    if eos_token:
        prompt = f"{prompt}{eos_token}"
    return prompt


def format_rag_inference_prompt(context: str, question: str) -> str:
    """
    Format context and question into the prompt ready for model generation.
    """
    return RAG_INFERENCE_TEMPLATE.format(
        context=context.strip(),
        question=question.strip(),
    )


def format_dataset_for_sft(
    records: List[Dict[str, str]], eos_token: str = ""
) -> List[Dict[str, str]]:
    """
    Transforms a list of raw records into a list of dicts with a 'text' field
    compatible with HuggingFace TRL SFTTrainer.
    """
    formatted = []
    for r in records:
        text = format_rag_record(r, eos_token=eos_token)
        formatted.append({"text": text})
    return formatted

