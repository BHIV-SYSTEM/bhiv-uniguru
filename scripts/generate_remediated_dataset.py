"""
Remediation Dataset Generator for UniGuru Marathi Indic-SQuAD
Reads raw verified train.json and val.json from backend/data/raw/indic_squad/marathi/
Outputs:
- data/training/indic_squad_mr_train_remediated.jsonl
- data/validation/indic_squad_mr_val_remediated.jsonl
- reports/remediation_dataset_summary.json
"""
import json
import re
import sys
from pathlib import Path
from collections import Counter

_PROJECT_ROOT = Path(__file__).resolve().parent.parent if "__file__" in locals() else Path(r"C:\Ganesh_149\uniguru\bhiv-uniguru")
sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.prepare_indic_squad import stream_json_array_records

ABSTENTION_TARGET = "दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही."

def clean_answer_span(ans: str) -> str:
    cleaned = ans.strip()
    # Strip trailing commas, colons, semicolons
    cleaned = re.sub(r'[,:;]+$', '', cleaned).strip()
    # If starts with unbalanced open paren and no close paren, strip leading paren
    if cleaned.startswith("(") and ")" not in cleaned:
        cleaned = cleaned[1:].strip()
    if cleaned.startswith('"') and cleaned.count('"') == 1:
        cleaned = cleaned[1:].strip()
    if cleaned.endswith('"') and cleaned.count('"') == 1:
        cleaned = cleaned[:-1].strip()
    return cleaned

def generate_remediated_split(raw_file: Path, out_file: Path, split_name="train"):
    print(f"\nProcessing {split_name} from {raw_file}...")
    seen_pairs = set()
    
    total_raw = 0
    answerable_count = 0
    unanswerable_count = 0
    discarded_whitespace = 0
    discarded_duplicates = 0
    discarded_span_errors = 0
    discarded_known_noise = 0
    cleaned_spans_count = 0
    
    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    with out_file.open("w", encoding="utf-8") as f_out:
        for rec in stream_json_array_records(raw_file):
            total_raw += 1
            rec_id = str(rec.get("id") or "").strip()
            title = str(rec.get("title") or "").strip()
            context = str(rec.get("context") or "").strip()
            question = str(rec.get("question") or "").strip()
            
            if not context or not question:
                continue
                
            dedup_key = (context, question)
            if dedup_key in seen_pairs:
                discarded_duplicates += 1
                continue
            seen_pairs.add(dedup_key)
            
            # Check for known noise ID
            if rec_id == "5a8cc8f2fd22b3001a8d8e6a":
                discarded_known_noise += 1
                continue
                
            answers = rec.get("answers", {})
            ans_texts = answers.get("text", [])
            
            # Case 1: Genuine Unanswerable
            if not isinstance(ans_texts, list) or len(ans_texts) == 0:
                unanswerable_count += 1
                out_rec = {
                    "id": rec_id,
                    "title": title,
                    "context": context,
                    "question": question,
                    "answer": ABSTENTION_TARGET,
                    "is_unanswerable": True,
                    "language": "mr",
                }
                f_out.write(json.dumps(out_rec, ensure_ascii=False) + "\n")
                continue
                
            # Case 2: Whitespace-only (Lost answer in machine translation)
            valid_answers = [str(t).strip() for t in ans_texts if str(t).strip()]
            if not valid_answers:
                discarded_whitespace += 1
                continue
                
            raw_primary = valid_answers[0]
            if not raw_primary.strip():
                discarded_whitespace += 1
                continue
            
            # Case 3: Verify span in context
            if raw_primary not in context:
                discarded_span_errors += 1
                continue
                
            # Clean span boundaries (punctuation / unbalanced parens)
            cleaned_primary = clean_answer_span(raw_primary)
            if cleaned_primary and cleaned_primary != raw_primary and cleaned_primary in context:
                final_ans = cleaned_primary
                cleaned_spans_count += 1
            else:
                final_ans = raw_primary
                
            if not final_ans.strip():
                discarded_whitespace += 1
                continue
            
            answerable_count += 1
            out_rec = {
                "id": rec_id,
                "title": title,
                "context": context,
                "question": question,
                "answer": final_ans,
                "is_unanswerable": False,
                "language": "mr",
            }
            f_out.write(json.dumps(out_rec, ensure_ascii=False) + "\n")

    summary = {
        "split": split_name,
        "total_raw": total_raw,
        "remediated_total": answerable_count + unanswerable_count,
        "answerable_count": answerable_count,
        "unanswerable_count": unanswerable_count,
        "unanswerable_percentage": round((unanswerable_count / (answerable_count + unanswerable_count)) * 100, 2),
        "discarded_whitespace": discarded_whitespace,
        "discarded_duplicates": discarded_duplicates,
        "discarded_span_errors": discarded_span_errors,
        "discarded_known_noise": discarded_known_noise,
        "cleaned_spans_count": cleaned_spans_count,
    }
    print(f"Summary for {split_name}: {summary}")
    return summary

if __name__ == "__main__":
    train_raw = Path(r"C:\Ganesh_149\uniguru\bhiv-uniguru\backend\data\raw\indic_squad\marathi\train.json")
    val_raw = Path(r"C:\Ganesh_149\uniguru\bhiv-uniguru\backend\data\raw\indic_squad\marathi\val.json")
    
    train_out = Path(r"C:\Ganesh_149\uniguru\bhiv-uniguru\data\training\indic_squad_mr_train_remediated.jsonl")
    val_out = Path(r"C:\Ganesh_149\uniguru\bhiv-uniguru\data\validation\indic_squad_mr_val_remediated.jsonl")
    
    s_train = generate_remediated_split(train_raw, train_out, "train")
    s_val = generate_remediated_split(val_raw, val_out, "val")
    
    report = {
        "train": s_train,
        "val": s_val,
        "abstention_target": ABSTENTION_TARGET
    }
    
    rep_path = Path(r"C:\Ganesh_149\uniguru\bhiv-uniguru\reports\remediation_dataset_summary.json")
    with open(rep_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nSaved remediation dataset summary to {rep_path}")
