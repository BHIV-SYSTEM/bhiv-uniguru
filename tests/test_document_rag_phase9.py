"""
UniGuru Phase 9 — Comprehensive Document-Scoped RAG Functional Test Suite
Tests:
  1. Upload TXT and request summary -> Complete grounded summary
  2. Upload DOCX and request summary -> Complete grounded summary
  3. Upload text-based PDF and request summary -> Complete grounded summary
  4. Ask question whose answer is in the document -> Correct grounded answer
  5. Ask about a particular chapter -> Relevant chapter explanation
  6. Ask about absent information -> Honest missing-information response
  7. Ask follow-up without re-uploading -> Same document remains accessible
  8. Upload two documents and compare them -> Evidence from both documents
  9. Ask in English about Marathi document -> English grounded answer
  10. Ask in Marathi about English document -> Marathi grounded answer
  11. Ask general question without attachment -> General Qwen answer
"""
from __future__ import annotations

import io
import json
import os
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)

import re
import sys
import time
import zipfile
from pathlib import Path
import requests

# Create session without ambient proxy
session = requests.Session()
session.trust_env = False
requests.get = session.get
requests.post = session.post

BACKEND_URL = "http://127.0.0.1:8000"

def create_sample_pdf(file_path: Path, text: str):
    """Generates a standard compliant text-based PDF using pypdf/fitz or raw PDF stream."""
    try:
        from pypdf import PdfWriter
        # If PdfWriter can't write raw text directly, create standard PDF structure
        writer = PdfWriter()
        # Create minimal PDF with text
        page = writer.add_blank_page(width=612, height=792)
    except Exception:
        pass

    # Standard clean raw PDF stream with stream text
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
        b"2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj\n"
        b"3 0 obj <</Type /Page /Parent 2 0 R /Resources <</Font <</F1 4 0 R>>>> /MediaBox [0 0 612 792] /Contents 5 0 R>> endobj\n"
        b"4 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj\n"
        b"5 0 obj <</Length 120>> stream\n"
        b"BT\n/F1 14 Tf\n50 700 Td\n(Chapter 1: Principles of Quantum Computing) Tj\n"
        b"0 -30 Td\n(Qubits can exist in superposition of state 0 and 1.) Tj\n"
        b"0 -30 Td\n(Entanglement links qubit pairs regardless of physical distance.) Tj\n"
        b"ET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f \n"
        b"0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \n"
        b"0000000230 00000 n \n0000000305 00000 n \ntrailer <</Size 6 /Root 1 0 R>>\nstartxref\n478\n%%EOF\n"
    )
    file_path.write_bytes(pdf_bytes)


def create_sample_docx(file_path: Path, paragraphs: list[str]):
    """Creates a valid .docx file containing paragraphs using standard OpenXML structure."""
    body_xml = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    doc_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:body>{body_xml}</w:body>'
        '</w:document>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '</Types>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '</Relationships>'
    )
    with zipfile.ZipFile(file_path, "w") as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc_xml)


def run_tests():
    print("=" * 60)
    print("STARTING UNIGURU PHASE 9 DOCUMENT RAG FUNCTIONAL TEST SUITE")
    print("=" * 60)

    test_dir = Path("backend/data/uploaded_docs/test_samples")
    test_dir.mkdir(parents=True, exist_ok=True)

    test_records = []

    # -------------------------------------------------------------
    # 1. Upload TXT and request summary
    # -------------------------------------------------------------
    print("\n--- Test 1: Upload TXT and request summary ---")
    txt_path = test_dir / "sample_climate.txt"
    txt_content = (
        "Chapter 1: Global Climate Systems and Carbon Cycles\n"
        "The greenhouse effect traps solar infrared radiation within Earth's troposphere.\n"
        "Carbon dioxide (CO2) concentrations have exceeded 420 parts per million.\n\n"
        "Chapter 2: Oceanic Acidification\n"
        "Oceans absorb approximately 30 percent of anthropogenic CO2 emissions, forming carbonic acid.\n"
        "This decreases seawater pH and harms marine calcifying organisms like corals."
    )
    txt_path.write_text(txt_content, encoding="utf-8")

    files = {"file": ("sample_climate.txt", open(txt_path, "rb"), "text/plain")}
    up1 = requests.post(f"{BACKEND_URL}/chat/upload", files=files, timeout=30).json()
    chat_id1 = up1["chatId"]
    doc_id1 = up1["document"]["document_id"]
    print(f"Uploaded TXT: ID={doc_id1}, Chars={up1['document']['char_count']}, Chunks={up1['document']['chunk_count']}")

    res1 = requests.post(f"{BACKEND_URL}/chat/new", json={"message": "give me summary of this document.", "chatId": chat_id1}, timeout=60).json()
    ans1 = res1.get("aiResponse", {}).get("content", "")
    chunks1 = res1.get("aiResponse", {}).get("metadata", {}).get("retrieved_chunks", [])
    print(f"Summary Response:\n{ans1[:200]}...")
    pass1 = "climate" in ans1.lower() or "greenhouse" in ans1.lower() or "ocean" in ans1.lower()
    test_records.append({
        "test": "1. Upload TXT and request summary",
        "format": "TXT",
        "file_name": "sample_climate.txt",
        "file_id": doc_id1,
        "char_count": up1["document"]["char_count"],
        "chunk_count": up1["document"]["chunk_count"],
        "retrieved_chunks": len(chunks1),
        "status": "PASS" if pass1 else "FAIL",
        "answer": ans1[:300]
    })

    # -------------------------------------------------------------
    # 2. Upload DOCX and request summary
    # -------------------------------------------------------------
    print("\n--- Test 2: Upload DOCX and request summary ---")
    docx_path = test_dir / "sample_robotics.docx"
    create_sample_docx(docx_path, [
        "Chapter 1: Autonomous Robotics and Kinematics",
        "Forward kinematics determines the end-effector position from joint angles.",
        "Inverse kinematics calculates the required joint angles for a desired target position.",
        "Chapter 2: Sensor Fusion and Path Planning",
        "Extended Kalman Filters merge noisy IMU and wheel odometry telemetry.",
        "A-star and Rapidly-exploring Random Trees provide collision-free trajectory generation."
    ])

    files = {"file": ("sample_robotics.docx", open(docx_path, "rb"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    up2 = requests.post(f"{BACKEND_URL}/chat/upload", files=files, timeout=30).json()
    chat_id2 = up2["chatId"]
    doc_id2 = up2["document"]["document_id"]
    print(f"Uploaded DOCX: ID={doc_id2}, Chars={up2['document']['char_count']}, Chunks={up2['document']['chunk_count']}")

    res2 = requests.post(f"{BACKEND_URL}/chat/new", json={"message": "give me summary of this document.", "chatId": chat_id2}, timeout=60).json()
    ans2 = res2.get("aiResponse", {}).get("content", "")
    print(f"DOCX Summary Response:\n{ans2[:200]}...")
    pass2 = "kinematics" in ans2.lower() or "robot" in ans2.lower()
    test_records.append({
        "test": "2. Upload DOCX and request summary",
        "format": "DOCX",
        "file_name": "sample_robotics.docx",
        "file_id": doc_id2,
        "char_count": up2["document"]["char_count"],
        "chunk_count": up2["document"]["chunk_count"],
        "status": "PASS" if pass2 else "FAIL",
        "answer": ans2[:300]
    })

    # -------------------------------------------------------------
    # 3. Upload text-based PDF and request summary
    # -------------------------------------------------------------
    print("\n--- Test 3: Upload text-based PDF and request summary ---")
    pdf_path = test_dir / "sample_quantum.pdf"
    create_sample_pdf(pdf_path, "")

    files = {"file": ("sample_quantum.pdf", open(pdf_path, "rb"), "application/pdf")}
    up3 = requests.post(f"{BACKEND_URL}/chat/upload", files=files, timeout=30).json()
    chat_id3 = up3["chatId"]
    doc_id3 = up3["document"]["document_id"]
    print(f"Uploaded PDF: ID={doc_id3}, Chars={up3['document']['char_count']}, Chunks={up3['document']['chunk_count']}")

    res3 = requests.post(f"{BACKEND_URL}/chat/new", json={"message": "give me summary of this document.", "chatId": chat_id3}, timeout=60).json()
    ans3 = res3.get("aiResponse", {}).get("content", "")
    print(f"PDF Summary Response:\n{ans3[:200]}...")
    pass3 = "quantum" in ans3.lower() or "qubit" in ans3.lower()
    test_records.append({
        "test": "3. Upload text-based PDF and request summary",
        "format": "PDF",
        "file_name": "sample_quantum.pdf",
        "file_id": doc_id3,
        "char_count": up3["document"]["char_count"],
        "chunk_count": up3["document"]["chunk_count"],
        "status": "PASS" if pass3 else "FAIL",
        "answer": ans3[:300]
    })

    # -------------------------------------------------------------
    # 4. Ask question whose answer is in the document
    # -------------------------------------------------------------
    print("\n--- Test 4: Question whose answer is in the document ---")
    res4 = requests.post(f"{BACKEND_URL}/chat/new", json={"message": "from the document i provided, how much anthropogenic CO2 do oceans absorb?", "chatId": chat_id1}, timeout=60).json()
    ans4 = res4.get("aiResponse", {}).get("content", "")
    print(f"Grounded Q&A Answer:\n{ans4[:200]}...")
    pass4 = "30" in ans4 or "thirty" in ans4.lower()
    test_records.append({
        "test": "4. Question whose answer is in document",
        "format": "TXT",
        "file_name": "sample_climate.txt",
        "status": "PASS" if pass4 else "FAIL",
        "answer": ans4[:300]
    })

    # -------------------------------------------------------------
    # 5. Ask about a particular chapter
    # -------------------------------------------------------------
    print("\n--- Test 5: Ask about a particular chapter ---")
    res5 = requests.post(f"{BACKEND_URL}/chat/new", json={"message": "Explain the second chapter regarding Oceanic Acidification.", "chatId": chat_id1}, timeout=60).json()
    ans5 = res5.get("aiResponse", {}).get("content", "")
    print(f"Chapter 2 Explanation:\n{ans5[:200]}...")
    pass5 = "carbonic" in ans5.lower() or "ph" in ans5.lower() or "calcifying" in ans5.lower() or "acid" in ans5.lower()
    test_records.append({
        "test": "5. Ask about a particular chapter",
        "format": "TXT",
        "status": "PASS" if pass5 else "FAIL",
        "answer": ans5[:300]
    })

    # -------------------------------------------------------------
    # 6. Ask about absent information (honest missing information response)
    # -------------------------------------------------------------
    print("\n--- Test 6: Ask about absent information ---")
    res6 = requests.post(f"{BACKEND_URL}/chat/new", json={"message": "According to the document, what was the stock price of Apple in 1995?", "chatId": chat_id1}, timeout=60).json()
    ans6 = res6.get("aiResponse", {}).get("content", "")
    status6 = res6.get("aiResponse", {}).get("metadata", {}).get("verification_status")
    print(f"Absent Info Response: {ans6} (Status: {status6})")
    pass6 = "not contain" in ans6.lower() or "उपलब्ध नाही" in ans6 or status6 == "NO_VERIFIED_KNOWLEDGE"
    test_records.append({
        "test": "6. Ask about absent information",
        "format": "TXT",
        "status": "PASS" if pass6 else "FAIL",
        "answer": ans6
    })

    # -------------------------------------------------------------
    # 7. Ask follow-up without re-uploading (session persistence)
    # -------------------------------------------------------------
    print("\n--- Test 7: Follow-up without re-uploading ---")
    res7 = requests.post(f"{BACKEND_URL}/chat/new", json={"message": "What effect does it have on coral reefs?", "chatId": chat_id1}, timeout=60).json()
    ans7 = res7.get("aiResponse", {}).get("content", "")
    print(f"Follow-up Answer:\n{ans7[:200]}...")
    pass7 = "coral" in ans7.lower() or "calcifying" in ans7.lower() or "acid" in ans7.lower() or "harm" in ans7.lower()
    test_records.append({
        "test": "7. Follow-up without re-uploading",
        "format": "TXT",
        "status": "PASS" if pass7 else "FAIL",
        "answer": ans7[:300]
    })

    # -------------------------------------------------------------
    # 8. Upload two documents and compare them
    # -------------------------------------------------------------
    print("\n--- Test 8: Upload two documents and compare them ---")
    # Upload robotics doc to chat_id1 as second document
    files_rob = {"file": ("second_doc_robotics.docx", open(docx_path, "rb"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    requests.post(f"{BACKEND_URL}/chat/upload", files=files_rob, data={"chatId": chat_id1}, timeout=30)
    res8 = requests.post(f"{BACKEND_URL}/chat/new", json={"message": "Compare what the first document says about climate with what the second document says about robotics.", "chatId": chat_id1}, timeout=60).json()
    ans8 = res8.get("aiResponse", {}).get("content", "")
    print(f"Comparison Answer:\n{ans8[:200]}...")
    pass8 = ("climate" in ans8.lower() or "carbon" in ans8.lower()) and ("robot" in ans8.lower() or "kinematics" in ans8.lower())
    test_records.append({
        "test": "8. Upload two documents and compare them",
        "format": "TXT + DOCX",
        "status": "PASS" if pass8 else "FAIL",
        "answer": ans8[:300]
    })

    # -------------------------------------------------------------
    # 9. Ask in English about Marathi document
    # -------------------------------------------------------------
    print("\n--- Test 9: Ask in English about Marathi document ---")
    mr_path = test_dir / "sample_maharashtra.txt"
    mr_content = (
        "प्रकरण १: महाराष्ट्राचा भूगोल आणि नद्या\n"
        "गोदावरी ही महाराष्ट्रातील सर्वात मोठी नदी आहे. तिला दक्षिण गंगा असेही म्हणतात.\n"
        "गोदावरी नदीचा उगम नाशिक जिल्ह्यातील त्र्यंबकेश्वर येथे होतो.\n"
        "प्रकरण २: सह्याद्री पर्वत आणि किल्ले\n"
        "सह्याद्री पर्वतरांगेत छत्रपती शिवाजी महाराजांनी बांधलेले अनेक ऐतिहासिक किल्ले आहेत."
    )
    mr_path.write_text(mr_content, encoding="utf-8")
    files_mr = {"file": ("sample_maharashtra.txt", open(mr_path, "rb"), "text/plain")}
    up_mr = requests.post(f"{BACKEND_URL}/chat/upload", files=files_mr, timeout=30).json()
    chat_mr = up_mr["chatId"]

    res9 = requests.post(f"{BACKEND_URL}/chat/new", json={"message": "In English, explain where does the Godavari river originate according to the document?", "chatId": chat_mr}, timeout=60).json()
    ans9 = res9.get("aiResponse", {}).get("content", "")
    print(f"English response to Marathi doc:\n{ans9[:200]}...")
    # Check that response is in English and mentions Trimbakeshwar or Nashik
    dev_count = len(re.findall(r"[\u0900-\u097f]", ans9))
    lat_count = len(re.findall(r"[A-Za-z]", ans9))
    pass9 = lat_count > dev_count and ("trimbakeshwar" in ans9.lower() or "nashik" in ans9.lower() or "godavari" in ans9.lower())
    test_records.append({
        "test": "9. Ask in English about Marathi document",
        "format": "TXT (Marathi)",
        "status": "PASS" if pass9 else "FAIL",
        "answer": ans9[:300]
    })

    # -------------------------------------------------------------
    # 10. Ask in Marathi about English document
    # -------------------------------------------------------------
    print("\n--- Test 10: Ask in Marathi about English document ---")
    res10 = requests.post(f"{BACKEND_URL}/chat/new", json={"message": "या दस्तऐवजानुसार हरितगृह वायूचा परिणाम (greenhouse effect) काय करतो?", "chatId": chat_id1}, timeout=60).json()
    ans10 = res10.get("aiResponse", {}).get("content", "")
    print(f"Marathi response to English doc:\n{ans10[:200]}...")
    ans_body10 = ans10.split("**दस्तऐवज संदर्भ**")[0].split("**Document Sources**")[0]
    dev_count10 = len(re.findall(r"[\u0900-\u097f]", ans_body10))
    lat_count10 = len(re.findall(r"[A-Za-z]", ans_body10))
    pass10 = dev_count10 > lat_count10 and dev_count10 >= 3
    test_records.append({
        "test": "10. Ask in Marathi about English document",
        "format": "TXT (English)",
        "status": "PASS" if pass10 else "FAIL",
        "answer": ans10[:300]
    })

    # -------------------------------------------------------------
    # 11. General question without attachment
    # -------------------------------------------------------------
    print("\n--- Test 11: General question without attachment ---")
    # Fresh chat session with no documents
    res11 = requests.post(f"{BACKEND_URL}/chat/new", json={"message": "can you give me a simple programm code for a liner regression"}, timeout=60).json()
    ans11 = res11.get("aiResponse", {}).get("content", "")
    print(f"General question answer:\n{ans11[:200]}...")
    pass11 = "linear" in ans11.lower() and ("def" in ans11 or "model" in ans11 or "import" in ans11)
    test_records.append({
        "test": "11. General question without attachment",
        "format": "N/A",
        "status": "PASS" if pass11 else "FAIL",
        "answer": ans11[:300]
    })

    print("\n" + "=" * 60)
    print("PHASE 9 TEST SUMMARY")
    print("=" * 60)
    for t in test_records:
        print(f"[{t['status']}] {t['test']}")

    results_file = Path("tests/document_rag_phase9_results.json")
    results_file.write_text(json.dumps(test_records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDetailed Phase 9 test records saved to {results_file.resolve()}")

if __name__ == "__main__":
    run_tests()

