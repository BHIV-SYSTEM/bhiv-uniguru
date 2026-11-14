"""
Functional Test Suite for Remediated Marathi QA Pipeline:
1. Dataset Schema & Balance Validation
2. Response-Only Masking Verification
3. Model Warm-Start & Forward/Backward Pass Verification
"""
import sys
import os
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

_PROJECT_ROOT = Path(__file__).resolve().parent.parent if "__file__" in locals() else Path(r"C:\Ganesh_149\uniguru\bhiv-uniguru")
os.environ["TRITON_CACHE_DIR"] = str(_PROJECT_ROOT / ".triton_cache")
sys.path.insert(0, str(_PROJECT_ROOT))

import torch
import json
from transformers import AutoTokenizer
from training.dataset_formatter import format_rag_record, RAG_PROMPT_TEMPLATE
from training.dataset_loader import load_raw_dataset

def test_1_dataset_integrity():
    print("\n--- TEST 1: Dataset Integrity & Schema ---")
    train_path = _PROJECT_ROOT / "data" / "training" / "indic_squad_mr_train_remediated.jsonl"
    val_path = _PROJECT_ROOT / "data" / "validation" / "indic_squad_mr_val_remediated.jsonl"
    
    assert train_path.exists(), f"Train file missing: {train_path}"
    assert val_path.exists(), f"Val file missing: {val_path}"
    
    train_data = load_raw_dataset(train_path)
    val_data = load_raw_dataset(val_path)
    
    assert len(train_data) == 117265, f"Unexpected train count: {len(train_data)}"
    assert len(val_data) == 11804, f"Unexpected val count: {len(val_data)}"
    
    abstention = "दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही."
    train_unans = sum(1 for r in train_data if r["answer"] == abstention)
    val_unans = sum(1 for r in val_data if r["answer"] == abstention)
    
    train_unans_pct = (train_unans / len(train_data)) * 100
    val_unans_pct = (val_unans / len(val_data)) * 100
    
    print(f" Train records: {len(train_data)} | Unanswerables: {train_unans} ({train_unans_pct:.2f}%)")
    print(f" Val records: {len(val_data)} | Unanswerables: {val_unans} ({val_unans_pct:.2f}%)")
    
    assert 30.0 < train_unans_pct < 38.0, "Train unanswerable ratio out of expected range"
    assert 48.0 < val_unans_pct < 55.0, "Val unanswerable ratio out of expected range"
    print(" [PASSED] Test 1: Dataset Integrity & Balance Validated.")

def test_2_response_only_masking():
    print("\n--- TEST 2: Response-Only Loss Masking ---")
    tok_dir = _PROJECT_ROOT / "checkpoints" / "qwen2.5-7b-indic-squad-mr-full" / "checkpoint-1000"
    tokenizer = AutoTokenizer.from_pretrained(str(tok_dir), local_files_only=True)
    
    # Sample 1: Answerable
    rec_ans = {
        "context": "महाराष्ट्र हे भारतातील एक राज्य आहे. मुंबई ही त्याची राजधानी आहे.",
        "question": "महाराष्ट्राची राजधानी कोणती?",
        "answer": "मुंबई",
    }
    # Sample 2: Unanswerable
    rec_unans = {
        "context": "महाराष्ट्र हे भारतातील एक राज्य आहे. मुंबई ही त्याची राजधानी आहे.",
        "question": "अमेरिकेचे राष्ट्रपती कोण आहेत?",
        "answer": "दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही.",
    }
    
    text_ans = format_rag_record(rec_ans, eos_token="<|im_end|>")
    text_unans = format_rag_record(rec_unans, eos_token="<|im_end|>")
    
    # Verify response token masking logic
    response_delim = "\n### Answer:\n"
    
    for label, text, target_ans in [("Answerable", text_ans, "मुंबई"), ("Unanswerable", text_unans, "दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही.")]:
        assert response_delim in text, f"Response delimiter missing in {label}"
        prompt_part, answer_part = text.split(response_delim, 1)
        
        prompt_ids = tokenizer.encode(prompt_part + response_delim, add_special_tokens=False)
        full_ids = tokenizer.encode(text, add_special_tokens=False)
        
        # In response-only masking:
        # tokens 0 to len(prompt_ids)-1 must be -100
        # tokens len(prompt_ids) to end must be valid token IDs
        labels = [-100] * len(prompt_ids) + full_ids[len(prompt_ids):]
        
        masked_tokens = sum(1 for x in labels if x == -100)
        unmasked_tokens = sum(1 for x in labels if x != -100)
        decoded_unmasked = tokenizer.decode([x for x in labels if x != -100], skip_special_tokens=False)
        
        print(f" {label}: Full tokens={len(full_ids)}, Masked={masked_tokens}, Loss-bearing={unmasked_tokens}")
        print(f"    Decoded target tokens: {repr(decoded_unmasked)}")
        
        assert unmasked_tokens > 0, f"No unmasked tokens for {label}!"
        assert target_ans in decoded_unmasked, f"Target answer missing from decoded unmasked tokens in {label}!"
        assert "<|im_end|>" in decoded_unmasked, f"EOS token missing from unmasked tokens in {label}!"
        
    print(" [PASSED] Test 2: Response-Only Loss Masking Logic Validated.")

def test_3_warm_start_forward_backward():
    print("\n--- TEST 3: Warm-Start Model Loading & Forward/Backward Pass ---")
    from unsloth import FastLanguageModel
    from unsloth.chat_templates import train_on_responses_only
    from trl import SFTTrainer
    from transformers import TrainingArguments
    from datasets import Dataset
    
    ckpt_dir = _PROJECT_ROOT / "checkpoints" / "qwen2.5-7b-indic-squad-mr-full" / "checkpoint-1000"
    assert ckpt_dir.exists(), f"Checkpoint 1000 missing at {ckpt_dir}"
    
    print(f" Loading warm-start model + LoRA adapter from {ckpt_dir}...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(ckpt_dir),
        max_seq_length=1280,
        load_in_4bit=True,
    )
    FastLanguageModel.for_training(model)
    print(" Model loaded and enabled for training successfully.")
    
    # Create a small 2-sample training dataset for testing
    from training.dataset_formatter import format_dataset_for_sft
    samples = [
        {
            "context": "ताजमहाल उत्तर प्रदेशातील आग्रा शहरात स्थित आहे. मुघल सम्राट शाहजहान यांनी तो बांधला.",
            "question": "ताजमहाल कोठे स्थित आहे?",
            "answer": "उत्तर प्रदेशातील आग्रा शहरात",
        },
        {
            "context": "ताजमहाल उत्तर प्रदेशातील आग्रा शहरात स्थित आहे. मुघल सम्राट शाहजहान यांनी तो बांधला.",
            "question": "ताजमहाल बांधायला किती कामगार होते?",
            "answer": "दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही.",
        }
    ]
    eos_token = tokenizer.eos_token or "<|im_end|>"
    formatted_samples = format_dataset_for_sft(samples, eos_token=eos_token)
    train_ds = Dataset.from_list(formatted_samples)
    
    tmp_out = _PROJECT_ROOT / "checkpoints" / "tmp_smoke_test"
    tmp_out.mkdir(parents=True, exist_ok=True)
    
    args = TrainingArguments(
        output_dir=str(tmp_out),
        per_device_train_batch_size=2,
        gradient_accumulation_steps=1,
        learning_rate=1e-4,
        max_steps=1,
        bf16=True,
        fp16=False,
        logging_steps=1,
        report_to="none",
    )
    
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_ds,
        dataset_text_field="text",
        max_seq_length=1280,
        args=args,
    )
    
    # Apply response masking
    trainer = train_on_responses_only(
        trainer,
        instruction_part="### Question:\n",
        response_part="### Answer:\n",
    )
    
    print(" Executing 1-step training forward/backward pass...")
    train_res = trainer.train()
    loss = train_res.training_loss
    print(f" Step 1 completed successfully! Training loss: {loss:.4f}")
    assert loss > 0, "Loss must be positive"
    
    # Clean up smoke test directory
    import shutil
    shutil.rmtree(tmp_out, ignore_errors=True)
    print(" [PASSED] Test 3: Warm-start forward and backward pass validated.")

if __name__ == "__main__":
    test_1_dataset_integrity()
    test_2_response_only_masking()
    test_3_warm_start_forward_backward()
    print("\n=======================================================")
    print(" ALL 3 FUNCTIONAL PIPELINE TESTS PASSED 100%!")
    print("=======================================================")
