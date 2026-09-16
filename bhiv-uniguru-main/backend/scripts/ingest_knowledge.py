import os
import sqlite3
import hashlib
import argparse
import time
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime

from tqdm import tqdm
import numpy as np

# Optional dependencies handling
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import faiss
except ImportError:
    faiss = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None


class DatabaseManager:
    """Handles all SQLite database operations."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = self._init_db()

    def _init_db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Create indexed_files table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS indexed_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT UNIQUE,
                sha256 TEXT,
                indexed_time TEXT
            )
        ''')
        
        # Create chunks table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT,
                page_number INTEGER,
                text TEXT,
                domain TEXT,
                category TEXT,
                subcategory TEXT,
                topic TEXT,
                chapter TEXT,
                source TEXT,
                language TEXT,
                type TEXT,
                created_at TEXT
            )
        ''')
        conn.commit()
        return conn

    def is_file_indexed(self, file_name: str, file_hash: str) -> bool:
        cur = self.conn.cursor()
        cur.execute("SELECT sha256 FROM indexed_files WHERE file_name = ?", (file_name,))
        row = cur.fetchone()
        if row and row[0] == file_hash:
            return True
        return False

    def mark_file_indexed(self, file_name: str, file_hash: str):
        cur = self.conn.cursor()
        now = datetime.utcnow().isoformat()
        cur.execute('''
            INSERT INTO indexed_files (file_name, sha256, indexed_time)
            VALUES (?, ?, ?)
            ON CONFLICT(file_name) DO UPDATE SET sha256=excluded.sha256, indexed_time=excluded.indexed_time
        ''', (file_name, file_hash, now))
        self.conn.commit()

    def insert_chunks(self, chunks_data: List[Dict[str, Any]]) -> List[int]:
        cur = self.conn.cursor()
        ids = []
        now = datetime.utcnow().isoformat()
        
        for data in chunks_data:
            cur.execute('''
                INSERT INTO chunks (
                    file_name, page_number, text, domain, category, 
                    subcategory, topic, chapter, source, language, type, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['file_name'],
                data.get('page_number', 1),
                data['text'],
                data.get('domain', 'general'),
                data.get('category', ''),
                data.get('subcategory', ''),
                data.get('topic', ''),
                data.get('chapter', ''),
                data.get('source', 'knowledge'),
                data.get('language', 'English'),
                data.get('type', 'document'),
                now
            ))
            ids.append(cur.lastrowid)
        
        self.conn.commit()
        return ids

    def close(self):
        self.conn.close()


class TextChunker:
    """Intelligently chunks text, respecting Markdown and word limits."""
    
    def __init__(self, max_words: int = 400, overlap_words: int = 50):
        self.max_words = max_words
        self.overlap_words = overlap_words

    def _count_words(self, text: str) -> int:
        return len(text.split())

    def _split_into_logical_blocks(self, text: str) -> List[str]:
        """Splits text into paragraphs/headings while keeping code blocks intact."""
        lines = text.split('\n')
        blocks = []
        current_block = []
        in_code_block = False
        
        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                current_block.append(line)
                if not in_code_block:
                    blocks.append("\n".join(current_block))
                    current_block = []
                continue
                
            if in_code_block:
                current_block.append(line)
                continue
                
            # If not in code block, split by blank lines or headings
            if line.strip() == "" or re.match(r'^#{1,6}\s', line):
                if current_block:
                    blocks.append("\n".join(current_block))
                    current_block = []
                if line.strip() != "":
                    current_block.append(line) # Heading starts a new block
            else:
                current_block.append(line)
                
        if current_block:
            blocks.append("\n".join(current_block))
            
        # Filter out empty blocks
        return [b.strip() for b in blocks if b.strip()]

    def chunk_text(self, text: str) -> List[str]:
        blocks = self._split_into_logical_blocks(text)
        chunks = []
        current_chunk_blocks = []
        current_word_count = 0
        
        for block in blocks:
            block_words = self._count_words(block)
            
            # If a single block is larger than max_words, we must hard split it
            if block_words > self.max_words:
                if current_chunk_blocks:
                    chunks.append("\n\n".join(current_chunk_blocks))
                    current_chunk_blocks = []
                    current_word_count = 0
                    
                words = block.split()
                for i in range(0, len(words), self.max_words - self.overlap_words):
                    segment = " ".join(words[i:i + self.max_words])
                    chunks.append(segment)
                continue
                
            # If adding this block exceeds the limit, push the current chunk
            if current_word_count + block_words > self.max_words and current_chunk_blocks:
                chunks.append("\n\n".join(current_chunk_blocks))
                
                # Create overlap by keeping the last block(s) if they fit within overlap budget
                overlap_budget = self.overlap_words
                overlap_blocks = []
                for b in reversed(current_chunk_blocks):
                    bw = self._count_words(b)
                    if overlap_budget - bw >= 0:
                        overlap_blocks.insert(0, b)
                        overlap_budget -= bw
                    else:
                        break
                        
                current_chunk_blocks = overlap_blocks
                current_word_count = sum(self._count_words(b) for b in overlap_blocks)
                
            current_chunk_blocks.append(block)
            current_word_count += block_words
            
        if current_chunk_blocks:
            chunks.append("\n\n".join(current_chunk_blocks))
            
        return chunks


class FileParser:
    """Parses text from various file formats."""
    
    @staticmethod
    def compute_sha256(file_path: str) -> str:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    def extract_metadata(file_path: str, base_dir: str) -> Dict[str, str]:
        rel_path = os.path.relpath(file_path, base_dir)
        parts = Path(rel_path).parts
        
        domain = "general"
        type_str = "document"
        category = ""
        subcategory = ""
        source = "knowledge"
        
        if len(parts) > 0:
            root_folder = parts[0].lower()
            if root_folder == "balbharti":
                domain = "education"
                source = "Balbharati"
                type_str = "textbook"
                category = parts[1].replace("class_", "") if len(parts) > 1 else ""
                subcategory = parts[2] if len(parts) > 2 else ""
            elif root_folder in ["jain", "gurukul", "swaminarayan", "puranas"]:
                domain = "religion"
                source = root_folder.capitalize()
                category = parts[1] if len(parts) > 1 else ""
                subcategory = parts[2] if len(parts) > 2 else ""
            else:
                domain = "general"
                source = root_folder.capitalize()
                category = parts[1] if len(parts) > 1 else ""
                subcategory = parts[2] if len(parts) > 2 else ""

        chapter = Path(file_path).stem
        topic = chapter.replace("_", " ").title()
        
        return {
            "domain": domain,
            "type": type_str,
            "category": category,
            "subcategory": subcategory,
            "topic": topic,
            "chapter": chapter,
            "source": source,
            "language": "English"
        }

    @staticmethod
    def parse_pdf(file_path: str) -> List[Dict[str, Any]]:
        if not fitz:
            raise ImportError("PyMuPDF (fitz) is not installed.")
            
        doc = fitz.open(file_path)
        pages = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text("text").strip()
            if text:
                pages.append({"page_number": page_num + 1, "text": text})
        return pages

    @staticmethod
    def parse_text_file(file_path: str) -> List[Dict[str, Any]]:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        if text:
            return [{"page_number": 1, "text": text}]
        return []


class RAGIndexer:
    """Main pipeline for orchestrating the ingestion process."""
    
    def __init__(self, knowledge_dir: str, batch_size: int = 64):
        self.knowledge_dir = os.path.abspath(knowledge_dir)
        self.batch_size = batch_size
        
        base_rag_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "RAG"))
        os.makedirs(base_rag_dir, exist_ok=True)
        
        self.db_path = os.path.join(base_rag_dir, "chunks_v4.db")
        self.faiss_path = os.path.join(base_rag_dir, "faiss_index_v4.bin")
        
        self.db = DatabaseManager(self.db_path)
        self.chunker = TextChunker()
        
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
        self.index = self._load_or_create_faiss()

    def _load_or_create_faiss(self):
        if os.path.exists(self.faiss_path):
            return faiss.read_index(self.faiss_path)
        else:
            base_index = faiss.IndexFlatL2(self.embedding_dim)
            return faiss.IndexIDMap2(base_index)

    def save_faiss(self):
        faiss.write_index(self.index, self.faiss_path)

    def process_directory(self):
        start_time = time.time()
        
        all_files = []
        for root, _, files in os.walk(self.knowledge_dir):
            for file in files:
                if file.lower().endswith(('.md', '.txt', '.pdf')):
                    all_files.append(os.path.join(root, file))
                    
        print(f"Found {len(all_files)} files")
        
        total_indexed = 0
        total_chunks = 0
        
        # Batching containers
        chunk_batch_texts = []
        chunk_batch_db_ids = []
        
        def flush_batch():
            if not chunk_batch_texts:
                return
            embeddings = self.model.encode(chunk_batch_texts, batch_size=self.batch_size, show_progress_bar=False)
            faiss.normalize_L2(embeddings)
            id_array = np.array(chunk_batch_db_ids, dtype=np.int64)
            self.index.add_with_ids(embeddings, id_array)
            chunk_batch_texts.clear()
            chunk_batch_db_ids.clear()
        
        for file_path in tqdm(all_files, desc="Indexing files"):
            file_name = os.path.basename(file_path)
            try:
                file_hash = FileParser.compute_sha256(file_path)
                
                if self.db.is_file_indexed(file_name, file_hash):
                    print(f"\nSkipping already indexed: {file_name}")
                    continue
                    
                print(f"\nProcessing {file_name}")
                
                metadata = FileParser.extract_metadata(file_path, self.knowledge_dir)
                
                if file_name.lower().endswith('.pdf'):
                    pages = FileParser.parse_pdf(file_path)
                else:
                    pages = FileParser.parse_text_file(file_path)
                    
                file_chunks_data = []
                for page in pages:
                    chunks = self.chunker.chunk_text(page['text'])
                    for chunk in chunks:
                        chunk_meta = {**metadata, "file_name": file_name, "text": chunk, "page_number": page['page_number']}
                        file_chunks_data.append(chunk_meta)
                        
                if file_chunks_data:
                    # Save to SQLite
                    db_ids = self.db.insert_chunks(file_chunks_data)
                    
                    # Accumulate for FAISS batching
                    chunk_batch_texts.extend([c['text'] for c in file_chunks_data])
                    chunk_batch_db_ids.extend(db_ids)
                    
                    if len(chunk_batch_texts) >= self.batch_size:
                        flush_batch()
                        
                    self.db.mark_file_indexed(file_name, file_hash)
                    
                    print(f"Added {len(file_chunks_data)} chunks")
                    total_chunks += len(file_chunks_data)
                    total_indexed += 1
                else:
                    print(f"No text extracted from {file_name}")
                    
            except Exception as e:
                logging.error(f"Failed to process {file_name}: {str(e)}")
                continue
                
        flush_batch() # flush remaining
        self.save_faiss()
        self.db.close()
        
        elapsed = time.time() - start_time
        print("\nFinished")
        print(f"Files Indexed: {total_indexed}")
        print(f"Chunks Created: {total_chunks}")
        print(f"Time: {int(elapsed)} seconds")


def main():
    parser = argparse.ArgumentParser(description="Ingest Knowledge files into RAG system")
    parser.add_argument("--dir", type=str, required=True, help="Directory containing knowledge files")
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size for embedding generation")
    args = parser.parse_args()

    if not all([faiss, SentenceTransformer]):
        print("Missing required libraries: faiss, sentence-transformers, tqdm")
        return

    indexer = RAGIndexer(knowledge_dir=args.dir, batch_size=args.batch_size)
    indexer.process_directory()


if __name__ == "__main__":
    main()
