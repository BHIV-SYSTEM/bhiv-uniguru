# Yashika OCR Retrieval Phase

## Overview
This phase handles the ingestion, parsing, and chunking of complex OCR-scanned documents provided in JSON format. This forms the foundation of the knowledge base for our retrieval-augmented generation pipeline.

## Key Mechanisms
1. **Document Loading**: The system systematically parses OCR-processed outputs (transcribed into JSON payloads). These sources frequently span multiple languages including Sanskrit, Hindi, Tamil, Telugu, German, and English.
2. **Data Cleansing & Normalization**: Extracted text blocks undergo rigorous cleaning to remove common OCR artifacts, broken Unicode characters, and fragmented line breaks to prepare it for seamless downstream processing.
3. **Script-Aware Chunking**: To correctly process Indic scripts and multilingual text, chunking algorithms are deployed that respect semantic boundaries (like verses or sentence endings) rather than relying solely on arbitrary token limits.
4. **Relational Storage Mapping**: The sanitized text chunks, paired with critical metadata such as `page_number` and `file_name`, are stored in a highly accessible local SQLite database (`chunks.db`). This ensures we maintain a deterministic link between the raw reference text and its eventual vector representation.

## Deliverables
- A robust, memory-efficient ingestion mechanism for massive OCR-derived JSON files.
- High-quality, semantically-chunked text artifacts with preserved metadata.
- Prepped SQLite database mapping structures directly aligned for vectorization.
