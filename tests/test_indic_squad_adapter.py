"""
Unit Tests for UniGuru IndicSQuAD Preprocessing Adapter.
Tests:
- Language resolution and aliases
- Exact span verification and fallback offset repair
- Multiple answer preservation in evaluation references
- Empty answer filtering (SQuAD 2.0 unanswerable questions)
- Missing context/question handling
- Duplicate question-context detection
- Local streaming JSON array parser
- Incremental split processing with metrics
- Cross-split leakage auditing
- Compatibility with training/dataset_loader.py and dataset_formatter.py
"""
import json
import pytest
from pathlib import Path

from scripts.prepare_indic_squad import (
    IndicSQuADAdapter,
    audit_cross_split_leakage,
    download_file_with_checksum,
    resolve_language,
    stream_json_array_records,
    validate_and_convert_record,
)
from training.dataset_formatter import format_dataset_for_sft, format_rag_record
from training.dataset_loader import load_raw_dataset


def test_resolve_language():
    name, code = resolve_language("Marathi")
    assert name == "Marathi"
    assert code == "mr"

    name, code = resolve_language("mr")
    assert name == "Marathi"
    assert code == "mr"

    name, code = resolve_language("Hindi")
    assert name == "Hindi"
    assert code == "hi"

    with pytest.raises(ValueError, match="Unsupported language"):
        resolve_language("klingon")


def test_validate_and_convert_record_exact_span():
    record = {
        "id": "q1",
        "title": "महाराष्ट्र",
        "context": "महाराष्ट्र हे भारतातील एक राज्य आहे. मुंबई ही त्याची राजधानी आहे.",
        "question": "महाराष्ट्राची राजधानी कोणती?",
        "answers": {
            "text": ["मुंबई"],
            "answer_start": [37],
        },
    }
    seen = set()
    train_rec, eval_ref, rejection, repaired, final_offset = validate_and_convert_record(record, "mr", seen)

    assert rejection is None
    assert repaired is False
    assert final_offset == 37
    assert train_rec is not None
    assert train_rec["context"] == record["context"]
    assert train_rec["question"] == record["question"]
    assert train_rec["answer"] == "मुंबई"
    assert train_rec["id"] == "q1"
    assert train_rec["language"] == "mr"

    assert eval_ref is not None
    assert eval_ref["primary_answer"] == "मुंबई"
    assert eval_ref["all_answers"] == ["मुंबई"]
    assert eval_ref["final_answer_start"] == 37
    assert ("महाराष्ट्र हे भारतातील एक राज्य आहे. मुंबई ही त्याची राजधानी आहे.", "महाराष्ट्राची राजधानी कोणती?") in seen


def test_validate_and_convert_record_repaired_span():
    # answer_start is wrong (0 instead of 37), but text exists in context
    record = {
        "id": "q2",
        "title": "महाराष्ट्र",
        "context": "महाराष्ट्र हे भारतातील एक राज्य आहे. मुंबई ही त्याची राजधानी आहे.",
        "question": "महाराष्ट्राची राजधानी कोणती?",
        "answers": {
            "text": ["मुंबई"],
            "answer_start": [0],  # Wrong offset
        },
    }
    seen = set()
    train_rec, eval_ref, rejection, repaired, final_offset = validate_and_convert_record(record, "mr", seen)

    assert rejection is None
    assert repaired is True
    assert final_offset == 37
    assert train_rec["answer"] == "मुंबई"


def test_validate_and_convert_record_multiple_answers():
    record = {
        "id": "q3",
        "title": "इतिहास",
        "context": "१५ ऑगस्ट १९४७ रोजी भारताला स्वातंत्र्य मिळाले.",
        "question": "भारताला स्वातंत्र्य कधी मिळाले?",
        "answers": {
            "text": ["१५ ऑगस्ट १९४७", "१९४७"],
            "answer_start": [0, 10],
        },
    }
    seen = set()
    train_rec, eval_ref, rejection, repaired, final_offset = validate_and_convert_record(record, "mr", seen)

    assert rejection is None
    assert train_rec["answer"] == "१५ ऑगस्ट १९४७"
    assert eval_ref["primary_answer"] == "१५ ऑगस्ट १९४७"
    assert eval_ref["all_answers"] == ["१५ ऑगस्ट १९४७", "१९४७"]


def test_validate_and_convert_record_empty_answers():
    # SQuAD 2.0 unanswerable question
    record = {
        "id": "q4",
        "title": "इतिहास",
        "context": "१५ ऑगस्ट १९४७ रोजी भारताला स्वातंत्र्य मिळाले.",
        "question": "अमेरिकेचे राष्ट्रपती कोण होते?",
        "answers": {
            "text": [],
            "answer_start": [],
        },
    }
    seen = set()
    train_rec, eval_ref, rejection, repaired, final_offset = validate_and_convert_record(record, "mr", seen)

    assert train_rec is None
    assert eval_ref is None
    assert rejection == "empty_answer_list"


def test_validate_and_convert_record_answer_not_in_context():
    record = {
        "id": "q5",
        "title": "विज्ञान",
        "context": "पाण्याचे रासायनिक सूत्र H2O आहे.",
        "question": "हवेमध्ये काय असते?",
        "answers": {
            "text": ["ऑक्सिजन"],
            "answer_start": [50],
        },
    }
    seen = set()
    train_rec, eval_ref, rejection, repaired, final_offset = validate_and_convert_record(record, "mr", seen)

    assert train_rec is None
    assert rejection == "answer_not_in_context"


def test_validate_and_convert_record_empty_context_or_question():
    seen = set()
    r1 = {"context": "", "question": "q?", "answers": {"text": ["a"]}}
    _, _, rej1, _, _ = validate_and_convert_record(r1, "mr", seen)
    assert rej1 == "empty_context"

    r2 = {"context": "ctx", "question": "  ", "answers": {"text": ["a"]}}
    _, _, rej2, _, _ = validate_and_convert_record(r2, "mr", seen)
    assert rej2 == "empty_question"


def test_validate_and_convert_record_duplicate_detection():
    record = {
        "id": "q6",
        "context": "पुणे हे विद्येचे माहेरघर आहे.",
        "question": "विद्येचे माहेरघर कोणते?",
        "answers": {"text": ["पुणे"], "answer_start": [0]},
    }
    seen = set()
    r1, _, rej1, _, _ = validate_and_convert_record(record, "mr", seen)
    assert rej1 is None

    # Duplicate insertion within same split
    r2, _, rej2, _, _ = validate_and_convert_record(record, "mr", seen)
    assert r2 is None
    assert rej2 == "duplicate_question_context"


def test_streaming_json_array_records_local(tmp_path):
    sample_data = [
        {"id": "1", "context": "C1", "question": "Q1", "answers": {"text": ["A1"], "answer_start": [0]}},
        {"id": "2", "context": "C2", "question": "Q2", "answers": {"text": ["A2"], "answer_start": [0]}},
        {"id": "3", "context": "C3", "question": "Q3", "answers": {"text": ["A3"], "answer_start": [0]}},
    ]
    file_path = tmp_path / "stream_test.json"
    file_path.write_text(json.dumps(sample_data, indent=2), encoding="utf-8")

    streamed = list(stream_json_array_records(file_path, max_records=2))
    assert len(streamed) == 2
    assert streamed[0]["id"] == "1"
    assert streamed[1]["id"] == "2"


def test_adapter_process_split_incremental_mock(tmp_path):
    mock_raw = [
        {"id": "1", "title": "T1", "context": "पुणे एक सुंदर शहर आहे.", "question": "कोणते शहर सुंदर आहे?", "answers": {"text": ["पुणे"], "answer_start": [0]}},
        {"id": "2", "title": "T2", "context": "मुंबई एक मोठी नगरी आहे.", "question": "कोणती मोठी नगरी आहे?", "answers": {"text": [], "answer_start": []}},  # Empty answer
        {"id": "3", "title": "T1", "context": "पुणे एक सुंदर शहर आहे.", "question": "कोणते शहर सुंदर आहे?", "answers": {"text": ["पुणे"], "answer_start": [0]}},  # Duplicate
        {"id": "4", "title": "T3", "context": "नाशिक गोदावरी काठी वसले आहे.", "question": "नाशिक कुठे वसले आहे?", "answers": {"text": ["गोदावरी काठी"], "answer_start": [7]}},
    ]
    raw_file = tmp_path / "mock_train.json"
    raw_file.write_text(json.dumps(mock_raw, ensure_ascii=False), encoding="utf-8")

    out_jsonl = tmp_path / "out_train.jsonl"
    out_eval = tmp_path / "out_eval.json"

    adapter = IndicSQuADAdapter(language="Marathi", raw_dir=tmp_path / "raw", output_dir=tmp_path)
    stats = adapter.process_split_incremental(
        split="train",
        target_sample_count=10,
        out_jsonl_path=out_jsonl,
        out_eval_refs_path=out_eval,
        local_override=raw_file,
    )

    assert stats["raw_records_examined"] == 4
    assert stats["valid_records_extracted"] == 2  # records 1 and 4
    assert stats["empty_answers_count"] == 1
    assert stats["duplicate_records_count"] == 1
    assert stats["unique_titles_count"] == 2  # T1 and T3
    assert stats["exact_offsets_count"] == 1
    assert stats["repaired_offsets_count"] == 1

    # Check written files
    assert out_jsonl.is_file()
    lines = [json.loads(l) for l in out_jsonl.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2
    assert lines[0]["answer"] == "पुणे"
    assert lines[1]["answer"] == "गोदावरी काठी"

    assert out_eval.is_file()
    eval_refs = json.loads(out_eval.read_text(encoding="utf-8"))
    assert len(eval_refs) == 2
    assert eval_refs[0]["id"] == "1"
    assert eval_refs[1]["id"] == "4"


def test_cross_split_leakage_audit(tmp_path):
    train_file = tmp_path / "train.jsonl"
    val_file = tmp_path / "val.jsonl"
    test_file = tmp_path / "test.jsonl"

    train_data = [
        {"id": "tr1", "context": "Context 1", "question": "Question 1", "answer": "Ans 1", "title": "Title 1"},
        {"id": "tr2", "context": "Context 2", "question": "Question 2", "answer": "Ans 2", "title": "Title 2"},
    ]
    val_data = [
        {"id": "val1", "context": "Context 3", "question": "Question 3", "answer": "Ans 3", "title": "Title 3"},
    ]
    test_data = [
        {"id": "test1", "context": "Context 4", "question": "Question 4", "answer": "Ans 4", "title": "Title 4"},
    ]

    for p, d in [(train_file, train_data), (val_file, val_data), (test_file, test_data)]:
        with p.open("w", encoding="utf-8") as f:
            for item in d:
                f.write(json.dumps(item) + "\n")

    leakage = audit_cross_split_leakage(train_file, val_file, test_file)
    assert leakage["clean"] is True
    assert leakage["total_cross_split_leaks"] == 0
    assert leakage["pairwise_comparisons"]["train_vs_val"]["id_overlap"] == 0


def test_compatibility_with_existing_dataset_loader_and_formatter(tmp_path):
    mock_raw = [
        {"id": "101", "context": "सौरऊर्जा ही अपारंपरिक ऊर्जा आहे.", "question": "सौरऊर्जा कोणती ऊर्जा आहे?", "answers": {"text": ["अपारंपरिक ऊर्जा"], "answer_start": [12]}},
        {"id": "102", "context": "पवनऊर्जा वाऱ्यापासून मिळते.", "question": "पवनऊर्जा कशापासून मिळते?", "answers": {"text": ["वाऱ्यापासून"], "answer_start": [10]}},
    ]
    raw_file = tmp_path / "mock_train.json"
    raw_file.write_text(json.dumps(mock_raw, ensure_ascii=False), encoding="utf-8")

    out_jsonl = tmp_path / "test_train.jsonl"
    adapter = IndicSQuADAdapter(language="Marathi", raw_dir=tmp_path / "raw", output_dir=tmp_path)
    adapter.process_split_incremental(
        split="train", target_sample_count=2, out_jsonl_path=out_jsonl, local_override=raw_file
    )

    # 1. Verify existing dataset_loader loads it without error
    loaded_records = load_raw_dataset(out_jsonl)
    assert len(loaded_records) == 2
    for item in loaded_records:
        assert set(item.keys()) == {"context", "question", "answer"}
        assert len(item["context"]) > 0
        assert len(item["question"]) > 0
        assert len(item["answer"]) > 0

    # 2. Verify existing dataset_formatter formats it into SFT prompt without error
    formatted = format_dataset_for_sft(loaded_records, eos_token="<|im_end|>")
    assert len(formatted) == 2
    assert "### System:" in formatted[0]["text"]
    assert "### Context:" in formatted[0]["text"]
    assert "सौरऊर्जा ही अपारंपरिक ऊर्जा आहे." in formatted[0]["text"]
    assert "### Question:" in formatted[0]["text"]
    assert "सौरऊर्जा कोणती ऊर्जा आहे?" in formatted[0]["text"]
    assert "### Answer:" in formatted[0]["text"]
    assert "अपारंपरिक ऊर्जा" in formatted[0]["text"]
    assert formatted[0]["text"].endswith("<|im_end|>")
