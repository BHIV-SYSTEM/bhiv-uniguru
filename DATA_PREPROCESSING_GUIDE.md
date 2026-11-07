# UniGuru Data Collection & Preprocessing Guide

This guide explains how to add new educational materials, run the modular 7-stage preprocessing pipeline, and prepare clean, structured datasets for both the **UniGuru RAG retrieval engine** and **Qwen 2.5 7B LLM fine-tuning** on your **NVIDIA GeForce RTX 3060 (12GB)** machine.

---

## 1. Directory Structure & Data Lifecycle

The data pipeline organizes documents across 6 dedicated lifecycle stages under `backend/data/`:

```
backend/data/
├── raw/            ← [Drop here] Original PDFs, textbooks, DOCX, TXT, YouTube transcripts, website scrapes
├── extracted/      ← Text extracted page-by-page (.txt / .json)
├── cleaned/        ← Normalized, header/footer stripped, and OCR-purified text (.json)
├── processed/      ← Validated documents with metadata, dedup registry & fine-tuning JSONL (.json / .jsonl)
├── chunks/         ← Section-aware semantic chunks for RAG vector indexing (.json / .jsonl)
└── rejected/       ← Audit logs for corrupted, scanned-only, or low-quality documents (.json)
```

### Data Formats Across Stages

| Stage / Folder | File Type | Format Details |
| :--- | :---: | :--- |
| **`raw/`** | `PDF`, `DOCX`, `TXT`, `MD`, `JSON` | Original textbooks, digital PDFs, Word files, YouTube transcripts. |
| **`extracted/`** | `TXT` / `JSON` | Raw text extracted per page with character counts. |
| **`cleaned/`** | `JSON` | Unicode-normalized (NFKC), broken hyphenation repaired, headers/footers removed. |
| **`processed/`** | `JSON` / `JSONL` | Validated document records with language, domain, and quality metadata. |
| **`chunks/`** | `JSON` / `JSONL` | Semantic chunks (500–1200 chars) with provenance and sentence boundary preservation. |
| **`rejected/`** | `JSON` | Error logs detailing why a document failed quality or deduplication gates. |

---

## 2. Supported Raw Input Types

Drop any of the following into `backend/data/raw/`:

1. **Textbooks & PDFs (`.pdf`)**: Digitized textbooks (e.g. Balbharti, NCERT). Scanned image-only PDFs are automatically detected and flagged for OCR.
2. **Word Documents (`.docx`)**: Curriculum syllabi, lesson plans, or lecture notes.
3. **Plain Text & Markdown (`.txt`, `.md`)**: Concept notes, articles, and documentation with optional YAML frontmatter.
4. **YouTube Transcripts (`.json`, `.jsonl`)**: Transcripts formatted as:
   ```json
   [
     {"text": "Photosynthesis is the process by which plants make glucose...", "start": 0.0, "duration": 4.2}
   ]
   ```
5. **Web Scrapes (`.json`)**: Articles with `title` and `content`/`body`/`article` keys.

---

## 3. The 7-Stage Preprocessing Pipeline

```
[Raw Document]
      │
      ▼
1. Document Extraction  ──────> saves to backend/data/extracted/
      │
      ▼
2. Text Cleaning        ──────> saves to backend/data/cleaned/
      │
      ▼
3. Deduplication Check  ──────> records hash in dedup_registry.json
      │
      ▼
4. Language Detection   ──────> specialized for Marathi, Hindi, English, Sanskrit
      │
      ▼
5. Quality Validation   ──────> if invalid, routes to backend/data/rejected/
      │
      ▼
6. Metadata Generation  ──────> saves to backend/data/processed/
      │
      ▼
7. Semantic Chunking    ──────> saves to backend/data/chunks/
      │
      ▼
[Fine-Tuning Export]    ──────> generates backend/data/processed/fine_tuning_rag.jsonl
```

### 1. Extraction (`DocumentExtractor`)
- PyMuPDF (`fitz`) handles multi-page PDF rendering and metadata extraction.
- Automatic scanned-PDF detection: documents with $< 30$ characters per page are flagged.
- Direct XML parsing extracts `.docx` paragraphs without heavy external dependencies.

### 2. Cleaning (`TextCleaner`)
- Unicode normalization via `NFKC`.
- Removes recurring running headers and footers (lines appearing on $> 40\%$ of pages).
- Strips standalone page numbers (e.g., `Page 14`, `14`, `--- 15 ---`, `[ 15 ]`).
- Reconnects broken hyphenation across line breaks (`exam-\nple` $\rightarrow$ `example`).
- Normalizes whitespace while preserving Devanagari punctuation (Danda `।`, Double Danda `॥`, Visarga `ः`).

### 3. Deduplication (`DocumentDeduplicator`)
- **Exact Hash**: SHA-256 hash over normalized text prevents re-processing identical files.
- **Near-Duplicate Detection**: 3-gram word shingling with Jaccard similarity ($\ge 0.90$).
- Tracks state in `backend/data/processed/dedup_registry.json`.

### 4. Language Detection (`LanguageDetector`)
Specialized offline classifier using script analysis and weighted linguistic markers:
- **Marathi**: Detects `ळ` (U+0933) and common tokens (`आहे`, `नाही`, `झाले`, `केले`, `त्यांच्या`, `म्हणून`, `इयत्ता`, `स्वाध्याय`).
- **Sanskrit**: Detects Visarga (`ः`), Avagraha (`ऽ`), Halanta (`्`), and classical terms (`अहम्`, `तस्य`, `अस्ति`, `भवति`, `धर्मः`, `विद्या`, `सत्यम्`, `वेद`, `श्लोक`).
- **Hindi**: Detects core stop words (`है`, `हैं`, `था`, `थी`, `थे`, `नहीं`, `और`, `का`, `के`, `की`, `से`, `में`, `पर`).
- **English**: Detects Latin script character dominance ($> 75\%$).

### 5. Quality Validation (`QualityValidator`)
Documents failing any of the following gates are safely quarantined to `backend/data/rejected/`:
- Minimum text length ($< 60$ characters).
- Minimum word count ($< 10$ words).
- Alphanumeric / script ratio ($< 50\%$ indicates corrupted OCR or binary garbage).
- Excessive Unicode replacement characters (`\ufffd`).
- Degenerate repetitive loops (Type-Token Ratio $< 0.15$).

### 6. Metadata Generation
Every processed file receives a rich JSON record under `backend/data/processed/{doc_id}.json` including:
`document_id`, `file_name`, `file_type`, `language`, `language_confidence`, `domain`, `quality_score`, `char_count`, `word_count`, `total_pages`, `sha256`.

### 7. Semantic Chunking (`TextChunker`)
- Sentence-aware boundaries (respecting `.`, `!`, `?`, `।`, and `॥`).
- Configurable chunk size (default: 1,000 characters) and overlap (default: 150 characters).
- Each chunk in `backend/data/chunks/{doc_id}_chunks.jsonl` contains:
  `chunk_id`, `document_id`, `chunk_index`, `page_number`, `text`, `language`, `domain`, and source metadata.

---

## 4. How to Run Preprocessing

### Option A: Process All Documents in `backend/data/raw/`
```powershell
python backend/preprocessing/pipeline.py
```

### Option B: Process a Single File
```powershell
python backend/preprocessing/pipeline.py --file backend/data/raw/math_grade_1.pdf
```

### Option C: Process and Export Qwen 2.5 Fine-Tuning Dataset
```powershell
python backend/preprocessing/pipeline.py --export-fine-tuning
```
*(Exports formatted JSONL pairs to `backend/data/processed/fine_tuning_rag.jsonl`)*

### Useful CLI Flags
- `--input-dir <path>`: Override the raw files directory.
- `--file <path>`: Process a specific document.
- `--domain <name>`: Explicit domain hint (e.g. `mathematics`, `physics`, `sanskrit`, `history`).
- `--export-fine-tuning`: Export all processed chunks into instruction-tuning format.

---

## 5. Integrating with Qwen 2.5 7B QLoRA Training

The preprocessed data links directly into the training pipeline created in Phase 1:

1. **Export the fine-tuning pairs**:
   ```powershell
   python backend/preprocessing/pipeline.py --export-fine-tuning
   ```
2. **Transfer or point the dataset to the training pipeline**:
   The generated file `backend/data/processed/fine_tuning_rag.jsonl` adheres strictly to the canonical RAG schema:
   ```json
   {
     "context": "Photosynthesis is the biological process by which green plants...",
     "question": "What key information is provided regarding Biology?",
     "answer": "Photosynthesis is the biological process by which green plants..."
   }
   ```
3. **Run a dry-run test on the newly generated dataset**:
   ```powershell
   python training/llm_trainer.py --dataset backend/data/processed/fine_tuning_rag.jsonl --dry-run
   ```
4. **Train on your RTX 3060 machine**:
   ```powershell
   python training/llm_trainer.py --dataset backend/data/processed/fine_tuning_rag.jsonl
   ```

