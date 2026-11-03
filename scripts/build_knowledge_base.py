"""
UniGuru Production Governed Knowledge Base Builder & Vector Indexer
===================================================================
Ingests, governs, and indexes all authoritative multi-domain sources into:
  - SQLite metadata/chunk store: backend/RAG/chunks.db (with FTS5 BM25 search)
  - FAISS semantic vector index: backend/RAG/faiss_index.bin (IndexIDMap)

Pipelines Covered:
  1. Sanskrit Civilizational Knowledge (backend/knowledge/sanskrit/*.md)
  2. Gurukul Curricula (backend/knowledge/gurukul/**/*.md)
  3. Jain Philosophy & Canon (backend/knowledge/jain/*.md)
  4. Swaminarayan Philosophy (backend/knowledge/swaminarayan/*.md)
  5. Quantum Sciences (backend/knowledge/quantum/**/*.md)
  6. Maharashtra Balbharati State Board Curriculum
  7. Kosha Canonical Texts (backend/data/kosha/*.jsonl)
  8. Mathematics (backend/knowledge/mathematics/*.md)
  9. Physics (backend/knowledge/physics/*.md)
  10. Chemistry (backend/knowledge/chemistry/*.md)
  11. Biology (backend/knowledge/biology/*.md)
  12. Computer Science (backend/knowledge/computer_science/*.md)
  13. Programming & Systems (backend/knowledge/programming/*.md)
  14. AI/ML & Deep Learning (backend/knowledge/ai_ml/*.md)
  15. History & Vedas (backend/knowledge/history/*.md)
  16. Geography (backend/knowledge/geography/*.md)
  17. Languages & GK (backend/knowledge/languages/*.md, general_knowledge/*.md)
  18. Authoritative Educational PDFs (backend/data/authoritative_pdfs/*.pdf)

Guarantees:
  - Deterministic 1-to-1 sync: SQLite chunk ID == FAISS vector ID
  - Normalized 384-d embeddings (all-MiniLM-L6-v2) for inner-product == cosine similarity
  - Complete provenance metadata: document_id, file_name, page_number, section, source, content_hash
"""

from __future__ import annotations

import os
import sys
import json
import re
import sqlite3
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
RAG_DIR = BACKEND_DIR / "RAG"
DB_PATH = RAG_DIR / "chunks.db"
FAISS_PATH = RAG_DIR / "faiss_index.bin"
METADATA_PATH = RAG_DIR / "index_metadata.json"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from loaders.pdf_ingestor import PDFIngestor

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def clean_markdown_text(text: str) -> str:
    """Clean markdown text while preserving structural meaning."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Extract YAML frontmatter metadata and body from markdown."""
    meta: Dict[str, Any] = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            header = parts[1]
            body = parts[2].strip()
            for line in header.strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    key = k.strip().lower()
                    val = v.strip().strip("\"'")
                    if key == "authority_score":
                        try:
                            meta[key] = float(val)
                        except ValueError:
                            meta[key] = 0.95
                    else:
                        meta[key] = val
    return meta, body


def chunk_markdown_file(file_path: Path, domain: str) -> List[Dict[str, Any]]:
    """Semantically chunk a Markdown file by its ## headers with metadata preservation."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"  [WARN] Failed to read {file_path}: {e}")
        return []

    frontmatter, body = parse_frontmatter(content)
    lines = body.splitlines()
    doc_title = frontmatter.get("title") or file_path.stem.replace("_", " ").title()
    for line in lines:
        if line.startswith("# ") and len(line) > 2:
            doc_title = line[2:].strip()
            break

    chunks: List[Dict[str, Any]] = []
    current_section = "Overview"
    current_lines: List[str] = []

    def flush_chunk(section_name: str, text_lines: List[str]):
        raw_text = clean_markdown_text("\n".join(text_lines))
        if len(raw_text) < 25:
            return
        chunk_text = f"Document: {doc_title} | Domain: {domain.title()} | Section: {section_name}\n{raw_text}"
        chunks.append({
            "document_id": str(file_path.relative_to(ROOT_DIR)).replace("\\", "/"),
            "file_name": file_path.name,
            "domain": domain,
            "book": doc_title,
            "board": "Authoritative Educational Reference",
            "grade": None,
            "subject": frontmatter.get("subject") or domain.title(),
            "chapter": doc_title,
            "section": section_name,
            "concept": doc_title,
            "page": 1,
            "language": "English",
            "text": chunk_text,
            "content_hash": stable_hash(chunk_text),
            "authority_score": frontmatter.get("authority_score", 0.95),
            "source_name": frontmatter.get("source_name", "Authoritative Educational Publication"),
            "source_url": frontmatter.get("source_url", ""),
            "license": frontmatter.get("license", "Educational Open Access"),
            "ingestion_date": time.strftime("%Y-%m-%d"),
        })

    for line in lines:
        if line.startswith("## "):
            if current_lines:
                flush_chunk(current_section, current_lines)
                current_lines = []
            current_section = line[3:].strip()
        elif not line.startswith("# "):
            current_lines.append(line)

    if current_lines:
        flush_chunk(current_section, current_lines)

    return chunks


def chunk_balbharti_record(rec: Dict[str, Any], source_file: str) -> Dict[str, Any]:
    """Turn a Balbharati curriculum record into a rich chunk."""
    concept = rec.get("concept") or "General Concept"
    chapter = rec.get("chapter") or "General Chapter"
    subject = rec.get("subject") or "General"
    grade = rec.get("grade")
    medium = rec.get("medium") or "English Medium"
    definition = rec.get("definition") or ""
    outcome = rec.get("learning_outcome") or ""
    examples = rec.get("examples") or []
    questions = rec.get("questions") or []
    lineage = rec.get("source_lineage") or {}

    ex_str = f"\nExamples: {'; '.join(examples)}" if examples else ""
    q_str = f"\nPractice Questions: {'; '.join(questions)}" if questions else ""
    out_str = f"\nLearning Outcome: {outcome}" if outcome else ""

    text = (
        f"Board: Maharashtra State Board (Balbharti) | Medium: {medium} | Grade: {grade} | Subject: {subject}\n"
        f"Chapter: {chapter} | Concept: {concept}\n"
        f"Definition: {definition}{out_str}{ex_str}{q_str}"
    )

    page = lineage.get("page") or 1
    return {
        "document_id": rec.get("record_id") or stable_hash(text)[:16],
        "file_name": source_file,
        "domain": "curriculum",
        "book": f"Balbharati {subject} Class {grade}",
        "board": "Maharashtra State Board (Balbharti)",
        "grade": grade,
        "subject": subject,
        "chapter": chapter,
        "section": lineage.get("section") or concept,
        "concept": concept,
        "page": page,
        "language": rec.get("language_variant") or "en",
        "text": text,
        "content_hash": stable_hash(text),
        "authority_score": 0.98,
        "source_name": "Maharashtra State Bureau of Textbook Production (Balbharti)",
        "source_url": "https://ebalbharati.in/",
        "license": "Government Textbook Open Educational",
        "ingestion_date": time.strftime("%Y-%m-%d"),
    }


def chunk_kosha_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Turn a Kosha entry into a structured chunk."""
    content = entry.get("clean_content") or entry.get("content") or ""
    source = entry.get("source") or "Kosha Puranic Canon"
    domain = entry.get("domain") or "puranas"
    tags = entry.get("tags") or []
    tag_str = f" | Tags: {', '.join(tags)}" if tags else ""

    text = f"Source: {source} | Domain: {domain.title()}{tag_str}\n{content.strip()}"
    return {
        "document_id": entry.get("knowledge_id") or stable_hash(text)[:16],
        "file_name": source,
        "domain": domain,
        "book": source,
        "board": "Vedic / Puranic Canon",
        "grade": None,
        "subject": domain.title(),
        "chapter": source,
        "section": tags[0] if tags else "General",
        "concept": tags[0].title() if tags else "General",
        "page": 1,
        "language": "en",
        "text": text,
        "content_hash": stable_hash(text),
        "authority_score": 0.95,
        "source_name": source,
        "source_url": "",
        "license": "Public Cultural Domain",
        "ingestion_date": time.strftime("%Y-%m-%d"),
    }


def collect_all_chunks() -> List[Dict[str, Any]]:
    """Gather chunks across all knowledge bases and deduplicate by content_hash."""
    all_chunks: List[Dict[str, Any]] = []
    seen_hashes: set = set()

    def add_chunk(chunk: Dict[str, Any]):
        h = chunk["content_hash"]
        if h in seen_hashes:
            return
        seen_hashes.add(h)
        all_chunks.append(chunk)

    # 1. Sanskrit
    print("\n--- 1. Collecting Sanskrit Knowledge Modules ---")
    sanskrit_dir = BACKEND_DIR / "knowledge" / "sanskrit"
    if sanskrit_dir.exists():
        for md_file in sorted(sanskrit_dir.glob("*.md")):
            if md_file.name.lower() == "readme.md":
                continue
            chunks = chunk_markdown_file(md_file, domain="sanskrit")
            for c in chunks:
                add_chunk(c)

    # 2. Gurukul
    print("\n--- 2. Collecting Gurukul Curricula ---")
    gurukul_dir = BACKEND_DIR / "knowledge" / "gurukul"
    if gurukul_dir.exists():
        for md_file in sorted(gurukul_dir.rglob("*.md")):
            chunks = chunk_markdown_file(md_file, domain=f"gurukul_{md_file.parent.name}")
            for c in chunks:
                add_chunk(c)

    # 3. Jain
    print("\n--- 3. Collecting Jain Canon & Philosophy ---")
    jain_dir = BACKEND_DIR / "knowledge" / "jain"
    if jain_dir.exists():
        for md_file in sorted(jain_dir.glob("*.md")):
            chunks = chunk_markdown_file(md_file, domain="jain")
            for c in chunks:
                add_chunk(c)

    # 4. Swaminarayan
    print("\n--- 4. Collecting Swaminarayan Philosophy ---")
    swami_dir = BACKEND_DIR / "knowledge" / "swaminarayan"
    if swami_dir.exists():
        for md_file in sorted(swami_dir.glob("*.md")):
            chunks = chunk_markdown_file(md_file, domain="swaminarayan")
            for c in chunks:
                add_chunk(c)

    # 5. Quantum
    print("\n--- 5. Collecting Quantum Sciences ---")
    quantum_dir = BACKEND_DIR / "knowledge" / "quantum"
    if quantum_dir.exists():
        for md_file in sorted(quantum_dir.rglob("*.md")):
            if md_file.name.lower() in ("readme.md", "kb_index.md"):
                continue
            chunks = chunk_markdown_file(md_file, domain="quantum")
            for c in chunks:
                add_chunk(c)

    # 6. Maharashtra Balbharati
    print("\n--- 6. Collecting Maharashtra Balbharati Curriculum ---")
    bf_path = ROOT_DIR / "masterdb" / "balbharti" / "canonical_dataset.json"
    if bf_path.exists():
        try:
            data = json.loads(bf_path.read_text(encoding="utf-8", errors="replace"))
            if isinstance(data, list):
                for rec in data:
                    chunk = chunk_balbharti_record(rec, source_file=bf_path.name)
                    add_chunk(chunk)
                print(f"  Loaded {len(data)} records from {bf_path.name}")
        except Exception as e:
            print(f"  [ERROR] Failed to load {bf_path}: {e}")

    # 7. Kosha Entries
    print("\n--- 7. Collecting Kosha Entries ---")
    kosha_file = BACKEND_DIR / "data" / "kosha" / "kosha_entries.jsonl"
    if kosha_file.exists():
        try:
            with kosha_file.open("r", encoding="utf-8", errors="replace") as f:
                k_count = 0
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    content = entry.get("clean_content") or entry.get("content") or ""
                    if len(content.strip().split()) >= 4:
                        chunk = chunk_kosha_entry(entry)
                        add_chunk(chunk)
                        k_count += 1
            print(f"  Loaded {k_count} multi-word entries from {kosha_file.name}")
        except Exception as e:
            print(f"  [ERROR] Failed to load {kosha_file}: {e}")

    # 8. Mathematics
    print("\n--- 8. Collecting Mathematics Knowledge ---")
    math_dir = BACKEND_DIR / "knowledge" / "mathematics"
    if math_dir.exists():
        for md in sorted(math_dir.glob("*.md")):
            chunks = chunk_markdown_file(md, domain="mathematics")
            for c in chunks:
                add_chunk(c)

    # 9. Physics
    print("\n--- 9. Collecting Physics Knowledge ---")
    physics_dir = BACKEND_DIR / "knowledge" / "physics"
    if physics_dir.exists():
        for md in sorted(physics_dir.glob("*.md")):
            chunks = chunk_markdown_file(md, domain="physics")
            for c in chunks:
                add_chunk(c)

    # 10. Chemistry
    print("\n--- 10. Collecting Chemistry Knowledge ---")
    chem_dir = BACKEND_DIR / "knowledge" / "chemistry"
    if chem_dir.exists():
        for md in sorted(chem_dir.glob("*.md")):
            chunks = chunk_markdown_file(md, domain="chemistry")
            for c in chunks:
                add_chunk(c)

    # 11. Biology
    print("\n--- 11. Collecting Biology Knowledge ---")
    bio_dir = BACKEND_DIR / "knowledge" / "biology"
    if bio_dir.exists():
        for md in sorted(bio_dir.glob("*.md")):
            chunks = chunk_markdown_file(md, domain="biology")
            for c in chunks:
                add_chunk(c)

    # 12. Computer Science
    print("\n--- 12. Collecting Computer Science Knowledge ---")
    cs_dir = BACKEND_DIR / "knowledge" / "computer_science"
    if cs_dir.exists():
        for md in sorted(cs_dir.glob("*.md")):
            chunks = chunk_markdown_file(md, domain="computer_science")
            for c in chunks:
                add_chunk(c)

    # 13. Programming & Systems
    print("\n--- 13. Collecting Programming & Systems Knowledge ---")
    prog_dir = BACKEND_DIR / "knowledge" / "programming"
    if prog_dir.exists():
        for md in sorted(prog_dir.glob("*.md")):
            chunks = chunk_markdown_file(md, domain="programming")
            for c in chunks:
                add_chunk(c)

    # 14. AI/ML & Deep Learning
    print("\n--- 14. Collecting AI/ML & Deep Learning Knowledge ---")
    aiml_dir = BACKEND_DIR / "knowledge" / "ai_ml"
    if aiml_dir.exists():
        for md in sorted(aiml_dir.glob("*.md")):
            chunks = chunk_markdown_file(md, domain="ai_ml")
            for c in chunks:
                add_chunk(c)

    # 15. History & Vedas
    print("\n--- 15. Collecting History & Vedas Knowledge ---")
    hist_dir = BACKEND_DIR / "knowledge" / "history"
    if hist_dir.exists():
        for md in sorted(hist_dir.glob("*.md")):
            dom = "vedas" if "veda" in md.name.lower() else "history"
            chunks = chunk_markdown_file(md, domain=dom)
            for c in chunks:
                add_chunk(c)

    # 16. Geography
    print("\n--- 16. Collecting Geography Knowledge ---")
    geo_dir = BACKEND_DIR / "knowledge" / "geography"
    if geo_dir.exists():
        for md in sorted(geo_dir.glob("*.md")):
            chunks = chunk_markdown_file(md, domain="geography")
            for c in chunks:
                add_chunk(c)

    # 17. Languages & General Knowledge
    print("\n--- 17. Collecting Languages & GK Knowledge ---")
    lang_dir = BACKEND_DIR / "knowledge" / "languages"
    if lang_dir.exists():
        for md in sorted(lang_dir.glob("*.md")):
            chunks = chunk_markdown_file(md, domain="language")
            for c in chunks:
                add_chunk(c)

    gk_dir = BACKEND_DIR / "knowledge" / "general_knowledge"
    if gk_dir.exists():
        for md in sorted(gk_dir.glob("*.md")):
            chunks = chunk_markdown_file(md, domain="general_knowledge")
            for c in chunks:
                add_chunk(c)

    # 18. Authoritative Educational PDFs
    print("\n--- 18. Ingesting Authoritative Educational PDFs ---")
    pdf_dir = BACKEND_DIR / "data" / "authoritative_pdfs"
    if pdf_dir.exists():
        pdf_ingestor = PDFIngestor()
        pdf_meta_map = {
            "ncert_physics_electromagnetism.pdf": {
                "source_name": "NCERT Class 12 Physics",
                "source_url": "https://ncert.nic.in/textbook.php",
                "domain": "physics",
                "subject": "Physics",
                "topic": "Electromagnetic Induction",
                "authority_score": 0.99,
            },
            "openstax_calculus_integration.pdf": {
                "source_name": "OpenStax Calculus 2e",
                "source_url": "https://openstax.org/",
                "domain": "mathematics",
                "subject": "Calculus",
                "topic": "Integration",
                "authority_score": 0.98,
            },
            "arxiv_quantum_computing_overview.pdf": {
                "source_name": "arXiv Quantum Physics",
                "source_url": "https://arxiv.org/",
                "domain": "quantum",
                "subject": "Quantum Computing",
                "topic": "Superposition & Entanglement",
                "authority_score": 0.98,
            },
            "indian_history_ancient_vedas.pdf": {
                "source_name": "Archaeological Survey of India & IGNCA",
                "source_url": "https://asi.nic.in/",
                "domain": "history",
                "subject": "Indian History & Vedas",
                "topic": "Vedas & Civilizations",
                "authority_score": 0.99,
            },
        }

        for pdf_file in sorted(pdf_dir.glob("*.pdf")):
            cfg = pdf_meta_map.get(pdf_file.name, {
                "source_name": "Authoritative Educational Publication",
                "source_url": "",
                "domain": "general",
                "subject": "General",
                "topic": "Education",
                "authority_score": 0.95,
            })
            pdf_chunks = pdf_ingestor.parse_pdf(
                file_path=pdf_file,
                source_name=cfg["source_name"],
                source_url=cfg["source_url"],
                domain=cfg["domain"],
                subject=cfg["subject"],
                topic=cfg["topic"],
                authority_score=cfg["authority_score"],
            )
            for c in pdf_chunks:
                # Map to schema keys
                c_formatted = {
                    "document_id": c["document_id"],
                    "file_name": c["file_name"],
                    "domain": c["domain"],
                    "book": c["title"],
                    "board": c["source_name"],
                    "grade": None,
                    "subject": c["subject"],
                    "chapter": c["title"],
                    "section": c["section"],
                    "concept": c["section"],
                    "page": c["page_number"],
                    "language": c["language"],
                    "text": c["text"],
                    "content_hash": c["content_hash"],
                    "authority_score": c["authority_score"],
                    "source_name": c["source_name"],
                    "source_url": c["source_url"],
                    "license": "Educational Open Access",
                    "ingestion_date": c["ingestion_date"],
                }
                add_chunk(c_formatted)
            print(f"  Ingested {len(pdf_chunks)} chunks from {pdf_file.name}")

    print(f"\n[TOTAL UNIQUE CHUNKS COLLECTED]: {len(all_chunks)}")
    return all_chunks


def setup_database(chunks: List[Dict[str, Any]]) -> None:
    """Populate chunks.db with governed relational schema, indexes, and FTS5."""
    import shutil
    RAG_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        backup_path = DB_PATH.with_suffix(".db.bak")
        try:
            shutil.copy2(DB_PATH, backup_path)
            print(f"[BACKUP] Existing SQLite DB backed up to {backup_path}")
        except Exception as e:
            print(f"[BACKUP NOTICE] Could not copy backup: {e}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS chunks_fts")
    cur.execute("DROP TABLE IF EXISTS chunks")
    cur.execute("DROP TABLE IF EXISTS documents")

    cur.execute("""
        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY,
            document_id TEXT,
            file_name TEXT,
            domain TEXT,
            book TEXT,
            board TEXT,
            grade INTEGER,
            subject TEXT,
            chapter TEXT,
            section TEXT,
            concept TEXT,
            page INTEGER,
            language TEXT,
            text TEXT,
            content_hash TEXT UNIQUE,
            authority_score REAL DEFAULT 0.95,
            source_name TEXT,
            source_url TEXT,
            license TEXT,
            ingestion_date TEXT
        )
    """)

    cur.execute("CREATE INDEX idx_chunks_domain ON chunks(domain)")
    cur.execute("CREATE INDEX idx_chunks_subject ON chunks(subject)")
    cur.execute("CREATE INDEX idx_chunks_grade ON chunks(grade)")
    cur.execute("CREATE INDEX idx_chunks_concept ON chunks(concept)")
    cur.execute("CREATE INDEX idx_chunks_authority ON chunks(authority_score)")

    # Virtual table for BM25 keyword search
    cur.execute("""
        CREATE VIRTUAL TABLE chunks_fts USING fts5(
            chunk_id UNINDEXED,
            book,
            subject,
            section,
            concept,
            text
        )
    """)

    insert_rows = []
    fts_rows = []
    for idx, c in enumerate(chunks, 1):
        insert_rows.append((
            idx,
            c["document_id"],
            c["file_name"],
            c["domain"],
            c["book"],
            c["board"],
            c["grade"],
            c["subject"],
            c["chapter"],
            c["section"],
            c["concept"],
            c["page"],
            c["language"],
            c["text"],
            c["content_hash"],
            c.get("authority_score", 0.95),
            c.get("source_name", "Authoritative Reference"),
            c.get("source_url", ""),
            c.get("license", "Educational Open Access"),
            c.get("ingestion_date", time.strftime("%Y-%m-%d")),
        ))
        fts_rows.append((
            idx,
            c["book"] or "",
            c["subject"] or "",
            c["section"] or "",
            c["concept"] or "",
            c["text"] or "",
        ))

    cur.executemany("""
        INSERT INTO chunks (
            id, document_id, file_name, domain, book, board, grade,
            subject, chapter, section, concept, page, language, text, content_hash,
            authority_score, source_name, source_url, license, ingestion_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, insert_rows)

    cur.executemany("""
        INSERT INTO chunks_fts (
            chunk_id, book, subject, section, concept, text
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, fts_rows)

    # Governance table: Documents registry
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,
            title TEXT,
            domain TEXT,
            subject TEXT,
            source_name TEXT,
            source_url TEXT,
            authority_score REAL,
            license TEXT,
            chunk_count INTEGER,
            ingestion_date TEXT
        )
    """)

    doc_stats: Dict[str, Dict[str, Any]] = {}
    for c in chunks:
        d_id = c["document_id"]
        if d_id not in doc_stats:
            doc_stats[d_id] = {
                "title": c["book"],
                "domain": c["domain"],
                "subject": c["subject"],
                "source_name": c.get("source_name", "Authoritative Reference"),
                "source_url": c.get("source_url", ""),
                "authority_score": c.get("authority_score", 0.95),
                "license": c.get("license", "Educational Open Access"),
                "chunk_count": 0,
                "ingestion_date": c.get("ingestion_date", time.strftime("%Y-%m-%d")),
            }
        doc_stats[d_id]["chunk_count"] += 1

    doc_rows = [
        (d_id, v["title"], v["domain"], v["subject"], v["source_name"], v["source_url"],
         v["authority_score"], v["license"], v["chunk_count"], v["ingestion_date"])
        for d_id, v in doc_stats.items()
    ]
    cur.executemany("""
        INSERT INTO documents (
            document_id, title, domain, subject, source_name, source_url,
            authority_score, license, chunk_count, ingestion_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, doc_rows)

    conn.commit()
    count = cur.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    fts_count = cur.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0]
    doc_count = cur.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    conn.close()
    print(f"[SQLITE]: Inserted {count} chunks, {fts_count} FTS5 rows, and {doc_count} documents into {DB_PATH}")


def build_faiss_index(chunks: List[Dict[str, Any]]) -> None:
    """Generate normalized embeddings and build FAISS IndexIDMap(IndexFlatIP)."""
    import shutil
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer

    if FAISS_PATH.exists():
        backup_path = FAISS_PATH.with_suffix(".bin.bak")
        shutil.copy2(FAISS_PATH, backup_path)
        print(f"[BACKUP] Existing FAISS index backed up to {backup_path}")

    print(f"\n[EMBEDDINGS]: Loading {EMBEDDING_MODEL_NAME}...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    dim = model.get_sentence_embedding_dimension()
    assert dim == EMBEDDING_DIM, f"Dimension mismatch: expected {EMBEDDING_DIM}, got {dim}"

    texts = [c["text"] for c in chunks]
    ids = np.array([idx for idx in range(1, len(chunks) + 1)], dtype=np.int64)

    print(f"[EMBEDDINGS]: Encoding {len(texts)} chunks in batches...")
    embeddings = model.encode(texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.array(embeddings, dtype=np.float32)

    # IndexIDMap with IndexFlatIP
    flat_index = faiss.IndexFlatIP(dim)
    index = faiss.IndexIDMap(flat_index)
    index.add_with_ids(embeddings, ids)

    if FAISS_PATH.exists():
        FAISS_PATH.unlink()

    faiss.write_index(index, str(FAISS_PATH))
    print(f"[FAISS]: Successfully written {index.ntotal} vectors to {FAISS_PATH}")

    # Write index metadata descriptor
    metadata = {
        "embedding_model": EMBEDDING_MODEL_NAME,
        "vector_dimension": dim,
        "index_type": "IndexIDMap(IndexFlatIP)",
        "total_chunks": len(chunks),
        "total_vectors": index.ntotal,
        "database": str(DB_PATH.name),
        "faiss_index": str(FAISS_PATH.name),
        "domains": sorted(list({c['domain'] for c in chunks})),
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"[METADATA]: Saved index metadata to {METADATA_PATH}")


def validate_index_sync() -> bool:
    """Strictly verify 1-to-1 sync between SQLite database and FAISS index."""
    import faiss

    print("\n--- Validating Database & FAISS Synchronization ---")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    db_count = cur.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    min_id, max_id = cur.execute("SELECT MIN(id), MAX(id) FROM chunks").fetchone()
    conn.close()

    index = faiss.read_index(str(FAISS_PATH))
    faiss_count = index.ntotal

    print(f"  SQLite Chunk Count: {db_count}")
    print(f"  SQLite ID Range:    [{min_id} ... {max_id}]")
    print(f"  FAISS Vector Count: {faiss_count}")

    if db_count != faiss_count:
        print(f"  [ERROR] MISMATCH: DB ({db_count}) != FAISS ({faiss_count})")
        return False
    if min_id != 1 or max_id != db_count:
        print(f"  [ERROR] Invalid SQLite ID sequence: {min_id} to {max_id}")
        return False

    print("  [PASS] Perfect 1-to-1 synchronization confirmed!")
    return True


def main():
    print("=" * 60)
    print("UNIGURU GOVERNED KNOWLEDGE BASE REBUILD & MULTI-DOMAIN INDEXING")
    print("=" * 60)

    chunks = collect_all_chunks()
    setup_database(chunks)
    build_faiss_index(chunks)
    valid = validate_index_sync()
    if not valid:
        sys.exit(1)

    print("\n" + "=" * 60)
    print("GOVERNED KNOWLEDGE BASE BUILD COMPLETED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    main()
