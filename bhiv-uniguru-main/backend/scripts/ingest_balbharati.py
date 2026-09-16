import os
import sqlite3
import json
import argparse
from typing import List, Dict, Any
import numpy as np

# Optional dependencies
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

def get_db_and_index_paths():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "RAG"))
    db_path = os.path.join(base_dir, "chunks.db")
    faiss_path = os.path.join(base_dir, "faiss_index.bin")
    return db_path, faiss_path

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Create table with new metadata columns if it doesn't exist
    cur.execute('''
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT,
            page_number INTEGER,
            text TEXT,
            class_level TEXT,
            subject TEXT,
            chapter TEXT,
            source TEXT,
            language TEXT
        )
    ''')
    
    # Try adding new columns if table already existed without them
    for col in ["class_level", "subject", "chapter", "source", "language"]:
        try:
            cur.execute(f"ALTER TABLE chunks ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass # Column exists
            
    conn.commit()
    return conn

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if len(chunk.strip()) > 50: # Skip very small chunks
            chunks.append(chunk)
    return chunks

def extract_metadata_from_path(file_path: str, base_dir: str) -> Dict[str, str]:
    # Expected: base_dir/class_10/science/book.pdf
    rel_path = os.path.relpath(file_path, base_dir)
    parts = rel_path.replace("\\", "/").split("/")
    
    class_level = "Unknown"
    subject = "Unknown"
    language = "English" # Default
    chapter = os.path.splitext(os.path.basename(file_path))[0]
    
    if len(parts) >= 2:
        class_level = parts[0].replace("class_", "")
        subject = parts[1].title()
        
    if "marathi" in file_path.lower():
        language = "Marathi"
    elif "hindi" in file_path.lower():
        language = "Hindi"
        
    return {
        "class_level": class_level,
        "subject": subject,
        "chapter": chapter,
        "source": "Balbharati",
        "language": language
    }

def process_pdf(file_path: str) -> List[Dict[str, Any]]:
    if not fitz:
        print("PyMuPDF (fitz) is not installed.")
        return []
        
    doc = fitz.open(file_path)
    extracted = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text")
        
        # Simple cleaning
        lines = text.split('\n')
        cleaned_lines = [line.strip() for line in lines if len(line.strip()) > 3]
        clean_text = " ".join(cleaned_lines)
        
        chunks = chunk_text(clean_text)
        for chunk in chunks:
            extracted.append({
                "page_number": page_num + 1,
                "text": chunk
            })
    return extracted

def main():
    parser = argparse.ArgumentParser(description="Ingest Balbharati textbook dataset")
    parser.add_argument("--dir", type=str, required=True, help="Directory containing Balbharati data (e.g., backend/knowledge/balbharati)")
    parser.add_argument("--model", type=str, default="all-MiniLM-L6-v2", help="Embedding model name")
    args = parser.parse_args()

    if not all([fitz, faiss, SentenceTransformer]):
        print("Missing required libraries: PyMuPDF, faiss, sentence-transformers")
        return
        
    db_path, faiss_path = get_db_and_index_paths()
    print(f"Using DB: {db_path}\nUsing FAISS: {faiss_path}")
    
    conn = init_db(db_path)
    cur = conn.cursor()
    
    model = SentenceTransformer(args.model)
    embedding_dim = model.get_sentence_embedding_dimension()
    
    if os.path.exists(faiss_path):
        index = faiss.read_index(faiss_path)
        print(f"Loaded existing FAISS index with {index.ntotal} vectors.")
    else:
        index = faiss.IndexFlatL2(embedding_dim)
        print("Created new FAISS index.")

    target_dir = os.path.abspath(args.dir)
    if not os.path.exists(target_dir):
        print(f"Directory {target_dir} does not exist.")
        return
        
    total_chunks_added = 0
    
    for root, _, files in os.walk(target_dir):
        for file in files:
            
                file_path = os.path.join(root, file)
                print(f"Processing: {file_path}")
                
                metadata = extract_metadata_from_path(file_path, target_dir)
                
                if file.lower().endswith(".pdf"):
                    chunks = process_pdf(file_path)
                else:
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                    text_chunks = chunk_text(text)
                    chunks = [{"page_number": 1, "text": c} for c in text_chunks]
                
                if not chunks:
                    continue
                    
                texts = [c["text"] for c in chunks]
                embeddings = model.encode(texts)
                faiss.normalize_L2(embeddings)
                
                for i, chunk_data in enumerate(chunks):
                    # Insert into SQLite
                    cur.execute('''
                        INSERT INTO chunks (file_name, page_number, text, class_level, subject, chapter, source, language)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        file, 
                        chunk_data["page_number"], 
                        chunk_data["text"],
                        metadata["class_level"],
                        metadata["subject"],
                        metadata["chapter"],
                        metadata["source"],
                        metadata["language"]
                    ))
                    
                    doc_id = cur.lastrowid
                    
                    # Add to FAISS. Index uses sequential IDs, but we can map them if we want.
                    # For faiss.IndexFlatL2, we add them directly. The index in FAISS is the row order.
                    # Since we want to map FAISS id to sqlite id, we can use IndexIDMap.
                    
                    # If it's a basic IndexFlatL2, we cannot pass custom IDs directly unless we wrap it.
                    # Wait, if faiss index is not IDMap, the IDs are 0, 1, 2...
                    # We should ensure the FAISS index uses IDMap to store our sqlite doc_id.
                    pass
                
                # To support custom IDs in FAISS, we must use IndexIDMap
                # Let's check if the current index is an IDMap.
                if not isinstance(index, faiss.IndexIDMap):
                    print("Wrapping index with IndexIDMap for custom IDs.")
                    id_map = faiss.IndexIDMap(index)
                    index = id_map
                
                # Now add all to FAISS with their actual SQLite IDs
                cur.execute("SELECT id FROM chunks ORDER BY id DESC LIMIT ?", (len(chunks),))
                recent_ids = [row[0] for row in cur.fetchall()]
                recent_ids.reverse() # ensure they match the order of `chunks`
                
                id_array = np.array(recent_ids, dtype=np.int64)
                index.add_with_ids(embeddings, id_array)
                
                conn.commit()
                total_chunks_added += len(chunks)
                print(f"Added {len(chunks)} chunks for {file}")

    if total_chunks_added > 0:
        faiss.write_index(index, faiss_path)
        print(f"Successfully ingested {total_chunks_added} chunks. Saved FAISS index.")
    else:
        print("No new chunks were added.")
        
    conn.close()

if __name__ == "__main__":
    main()
