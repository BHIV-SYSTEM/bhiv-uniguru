"""
UniGuru Curriculum Truth Validation Suite
Validates the entire curriculum authority layer with 42 truth integrity tests.

Run with:
    pytest tests/test_curriculum_truth_validation.py -v
"""

from __future__ import annotations

import json
import uuid
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest
from learning_runtime.canonical_runtime import execute_query
from scripts.run_textbook_reconstruction_validation import reconstruct_lineage

# Paths
AUTHORITY_DIR = ROOT / "curriculum" / "authority"
PROVENANCE_DIR = ROOT / "curriculum" / "provenance"
AUDITS_DIR = ROOT / "curriculum" / "audits"
CONTRACTS_DIR = ROOT / "backend" / "contracts"


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Phase 1: Verified Textbook Authority Registry Tests
# ---------------------------------------------------------------------------

def test_01_textbook_authority_registry_schema_v1():
    with open(AUTHORITY_DIR / "verified_textbook_authority_registry.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("$schema") is not None
    assert data.get("registry_id") == "verified_textbook_authority_registry_v1"


def test_02_textbook_authority_registry_has_four_books():
    with open(AUTHORITY_DIR / "verified_textbook_authority_registry.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data.get("textbooks", [])) == 4


def test_03_textbook_authority_registry_unique_ids():
    with open(AUTHORITY_DIR / "verified_textbook_authority_registry.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    ids = [tb.get("textbook_id") for tb in data.get("textbooks", [])]
    assert len(ids) == len(set(ids))


def test_04_textbook_authority_registry_no_synthetic():
    with open(AUTHORITY_DIR / "verified_textbook_authority_registry.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    for tb in data.get("textbooks", []):
        assert tb.get("authority_status") == "VERIFIED_AUTHORITY"


def test_05_textbook_authority_registry_publisher_balbharti():
    with open(AUTHORITY_DIR / "verified_textbook_authority_registry.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    for tb in data.get("textbooks", []):
        assert "Balbharti" in tb.get("publisher", "")


def test_06_textbook_authority_registry_valid_page_counts():
    with open(AUTHORITY_DIR / "verified_textbook_authority_registry.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    for tb in data.get("textbooks", []):
        assert isinstance(tb.get("page_count"), int)
        assert tb.get("page_count") > 100


def test_07_textbook_authority_registry_source_hashes_length():
    with open(AUTHORITY_DIR / "verified_textbook_authority_registry.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    for tb in data.get("textbooks", []):
        h = tb.get("source_hash")
        assert len(h) == 64
        # Assert it is a valid hex string
        int(h, 16)


def test_08_textbook_authority_registry_ocr_status_verified():
    with open(AUTHORITY_DIR / "verified_textbook_authority_registry.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    for tb in data.get("textbooks", []):
        assert tb.get("ocr_status") == "VERIFIED"


# ---------------------------------------------------------------------------
# Phase 2: Page-Level Provenance Registry Tests
# ---------------------------------------------------------------------------

def test_09_page_registry_total_pages_count():
    with open(PROVENANCE_DIR / "page_registry.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 630  # 156 + 164 + 142 + 168 = 630


def test_10_page_registry_unique_page_ids():
    with open(PROVENANCE_DIR / "page_registry.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    ids = [p.get("page_id") for p in data]
    assert len(ids) == len(set(ids))


def test_11_page_registry_valid_page_numbers():
    with open(PROVENANCE_DIR / "page_registry.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    for p in data:
        assert isinstance(p.get("page_number"), int)
        assert p.get("page_number") > 0


def test_12_page_registry_no_overlapping_page_numbers_per_book():
    with open(PROVENANCE_DIR / "page_registry.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    book_pages = {}
    for p in data:
        tb = p.get("textbook_id")
        num = p.get("page_number")
        if tb not in book_pages:
            book_pages[tb] = []
        assert num not in book_pages[tb]
        book_pages[tb].append(num)


def test_13_page_registry_content_hashes_unique():
    with open(PROVENANCE_DIR / "page_registry.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    hashes = [p.get("content_hash") for p in data]
    # In our generated dataset, all content hashes are distinct
    assert len(hashes) == len(set(hashes))


def test_14_page_registry_all_ocr_verified():
    with open(PROVENANCE_DIR / "page_registry.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    for p in data:
        assert p.get("ocr_status") == "VERIFIED"


def test_15_section_registry_count():
    with open(PROVENANCE_DIR / "section_registry.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) >= 5


def test_16_section_registry_non_empty_titles():
    with open(PROVENANCE_DIR / "section_registry.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    for s in data:
        assert s.get("section_title") != ""


def test_17_section_registry_page_ranges_well_formed():
    with open(PROVENANCE_DIR / "section_registry.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    for s in data:
        pr = s.get("page_range")
        assert "-" in pr
        parts = pr.split("-")
        assert len(parts) == 2
        start, end = int(parts[0]), int(parts[1])
        assert start <= end


def test_18_concept_page_mapping_has_required_concepts():
    with open(PROVENANCE_DIR / "concept_page_mapping.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "BALBHARTI_MATH_G1_MM_CONCEPT_001" in data
    assert "BALBHARTI_MATH_G1_MM_CONCEPT_002" in data
    assert "BALBHARTI_MATH_G2_MM_CONCEPT_001" in data


def test_19_concept_page_mapping_keys_are_concept_ids():
    with open(PROVENANCE_DIR / "concept_page_mapping.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    for k in data.keys():
        assert k.startswith("BALBHARTI_")


def test_20_concept_page_mapping_values_contain_required_fields():
    with open(PROVENANCE_DIR / "concept_page_mapping.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    for v in data.values():
        assert "textbook_id" in v
        assert "edition" in v
        assert "page_number" in v
        assert "chapter" in v
        assert "section" in v


def test_21_concept_page_mapping_page_numbers_in_range():
    with open(PROVENANCE_DIR / "concept_page_mapping.json", "r", encoding="utf-8") as f:
        mapping = json.load(f)
    with open(AUTHORITY_DIR / "verified_textbook_authority_registry.json", "r", encoding="utf-8") as f:
        auth = json.load(f)
    
    page_limits = {tb.get("textbook_id"): tb.get("page_count") for tb in auth.get("textbooks", [])}
    for v in mapping.values():
        tb_id = v.get("textbook_id")
        p_num = v.get("page_number")
        assert tb_id in page_limits
        assert 1 <= p_num <= page_limits[tb_id]


def test_22_exercise_page_mapping_has_required_exercises():
    with open(PROVENANCE_DIR / "exercise_page_mapping.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "BALBHARTI_MATH_G1_MM_CH01_EX001" in data
    assert "BALBHARTI_MATH_G1_MM_CH01_EX002" in data
    assert "BALBHARTI_MATH_G2_MM_CH02_EX001" in data


def test_23_exercise_page_mapping_structure():
    with open(PROVENANCE_DIR / "exercise_page_mapping.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    for v in data.values():
        assert "textbook_id" in v
        assert "page" in v
        assert "source_section" in v


def test_24_exercise_page_mapping_pages_in_range():
    with open(PROVENANCE_DIR / "exercise_page_mapping.json", "r", encoding="utf-8") as f:
        mapping = json.load(f)
    with open(AUTHORITY_DIR / "verified_textbook_authority_registry.json", "r", encoding="utf-8") as f:
        auth = json.load(f)
        
    page_limits = {tb.get("textbook_id"): tb.get("page_count") for tb in auth.get("textbooks", [])}
    for v in mapping.values():
        tb_id = v.get("textbook_id")
        p_num = v.get("page")
        assert tb_id in page_limits
        assert 1 <= p_num <= page_limits[tb_id]


# ---------------------------------------------------------------------------
# Phase 3: Runtime Response Contract Tests
# ---------------------------------------------------------------------------

def test_25_runtime_evidence_contract_schema_validity():
    with open(CONTRACTS_DIR / "runtime_evidence_contract.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("title") == "UniGuru Runtime Evidence Contract"
    assert "evidence_id" in data.get("required", [])


def test_26_runtime_response_contains_evidence_id():
    res = execute_query(query="What is counting?", grade=1, subject="Mathematics")
    eid = res.get("evidence_id")
    assert eid is not None
    # Verify it is a valid UUID
    uuid.UUID(eid)


def test_27_runtime_response_contains_textbook_id():
    res = execute_query(query="What is counting?", grade=1, subject="Mathematics")
    assert res.get("textbook_id") == "BALBHARTI_MATH_G1_MM"


def test_28_runtime_response_contains_edition():
    res = execute_query(query="What is counting?", grade=1, subject="Mathematics")
    assert res.get("edition") == "2023"


def test_29_runtime_response_contains_chapter():
    res = execute_query(query="What is counting?", grade=1, subject="Mathematics")
    assert res.get("chapter") == "Counting from 1 to 10"


def test_30_runtime_response_contains_section():
    res = execute_query(query="What is counting?", grade=1, subject="Mathematics")
    assert res.get("section") == "Number Recognition (1-5)"


def test_31_runtime_response_contains_page_numbers():
    res = execute_query(query="What is counting?", grade=1, subject="Mathematics")
    assert res.get("page_numbers") == [3]


def test_32_runtime_response_contains_source_hash():
    res = execute_query(query="What is counting?", grade=1, subject="Mathematics")
    assert len(res.get("source_hash", "")) == 64


def test_33_runtime_response_contains_retrieval_hash():
    res = execute_query(query="What is counting?", grade=1, subject="Mathematics")
    assert len(res.get("retrieval_hash", "")) == 64


def test_34_runtime_response_contains_lineage_hash():
    res = execute_query(query="What is counting?", grade=1, subject="Mathematics")
    tb = res.get("textbook_id")
    ed = res.get("edition")
    ch = res.get("chapter")
    sec = res.get("section")
    pgs = res.get("page_numbers")
    
    lineage_str = f"{tb}::{ed}::{ch}::{sec}::{pgs}"
    expected_hash = stable_hash(lineage_str)
    assert res.get("lineage_hash") == expected_hash


def test_35_runtime_response_verification_status():
    res = execute_query(query="What is counting?", grade=1, subject="Mathematics")
    assert res.get("verification_status") == "VERIFIED"


# ---------------------------------------------------------------------------
# Phase 4: Lineage Reconstruction Tests
# ---------------------------------------------------------------------------

def test_36_reconstruction_validation_confidence_for_math():
    proof = reconstruct_lineage("What is counting?")
    assert proof.get("reconstruction_confidence") == 1.0


def test_37_reconstruction_validation_chain_correctness():
    proof = reconstruct_lineage("What is counting?")
    chain = proof.get("lineage_chain", [])
    levels = [item.get("level") for item in chain]
    assert levels == ["publisher", "textbook", "edition", "chapter", "section", "pages"]
    for item in chain:
        if item.get("level") in ["textbook", "section", "pages"]:
            assert item.get("verified") is True


# ---------------------------------------------------------------------------
# Phase 5: Synthetic Dependency Audit Tests
# ---------------------------------------------------------------------------

def test_38_synthetic_audit_json_exists_and_flagged():
    with open(AUDITS_DIR / "synthetic_content_audit.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("audit_status") == "FLAGGED"


def test_39_synthetic_audit_reports_synthetic_records_count():
    with open(AUDITS_DIR / "synthetic_content_audit.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("summary", {}).get("total_synthetic_elements_detected", 0) > 2000


def test_40_synthetic_audit_scanned_expected_files():
    with open(AUDITS_DIR / "synthetic_content_audit.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    files = [find.get("file") for find in data.get("findings", [])]
    assert any("sample_ingestion_dataset.json" in f for f in files)


# ---------------------------------------------------------------------------
# Additional Truth Integrity Tests
# ---------------------------------------------------------------------------

def test_41_all_registered_concepts_have_matching_textbook():
    with open(PROVENANCE_DIR / "concept_page_mapping.json", "r", encoding="utf-8") as f:
        mapping = json.load(f)
    with open(AUTHORITY_DIR / "verified_textbook_authority_registry.json", "r", encoding="utf-8") as f:
        auth = json.load(f)
    
    allowed_tbs = {tb.get("textbook_id") for tb in auth.get("textbooks", [])}
    for v in mapping.values():
        assert v.get("textbook_id") in allowed_tbs


def test_42_no_silent_synthetic_content_in_registries():
    # Make sure none of our registries contain synthetic seed values
    registry_paths = [
        AUTHORITY_DIR / "verified_textbook_authority_registry.json",
        PROVENANCE_DIR / "page_registry.json",
        PROVENANCE_DIR / "section_registry.json",
        PROVENANCE_DIR / "concept_page_mapping.json",
        PROVENANCE_DIR / "exercise_page_mapping.json"
    ]
    for p in registry_paths:
        text = p.read_text(encoding="utf-8")
        assert "synthetic_expansion_seed" not in text
        assert "sample_seed" not in text
