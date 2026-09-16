# Yashika Embedding Phase

## Overview
This phase captures the deep semantic meaning of the processed OCR text chunks and transforms them into a high-dimensional vector space to facilitate rapid, context-aware similarity searches in the RAG pipeline.

## Key Mechanisms
1. **Data Ingestion**: The system pulls the sanitized text records from the SQLite database finalized in the OCR Retrieval Phase.
2. **Semantic Vectorization**: 
   - Employs open-source Sentence Transformer models (e.g., `all-MiniLM-L6-v2`, `multilingual-e5-large`, or `Vyakyarth`) to generate precise contextual embeddings for every text chunk.
3. **FAISS Indexing Strategy**: 
   - The generated high-dimensional numerical arrays are integrated directly into a local FAISS index (`faiss_index.bin`).
   - Using configurations like `IndexFlatIP` coupled with `IndexIDMap`, the vectors are explicitly mapped back to their original IDs in the SQLite `chunks.db`. This dual-architecture guarantees that vector matches instantly resolve to their exact deterministic text sources.
4. **Distance Normalization**: L2 normalization is applied ensuring that the vector inner-products accurately represent cosine similarities, optimizing the mathematical accuracy when locating relevant contexts.

## Deliverables
- A compiled, high-performance FAISS binary index capturing the semantic structure of the knowledge corpus.
- The underlying connective tissue that enables lightning-fast context retrieval during live user queries before gracefully falling back to LLM generation.
