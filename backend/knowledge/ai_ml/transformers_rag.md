---
domain: ai_ml
subdomain: deep_learning_and_llms
topic: transformers_and_rag
language: en
source: uniguru_aiml_guide
source_type: verified_handbook
difficulty: advanced
document_id: AIML_CORE_001
chunk_id: CHUNK_TRANSFORMERS_RAG
version: 1.0.0
created_at: 2026-10-02T11:45:00Z
---

# AI, Machine Learning, Transformers & Retrieval-Augmented Generation (RAG)

## 1. Machine Learning vs. Deep Learning vs. LLMs
- **Classical ML**: Supervised (Linear Regression, Random Forests, XGBoost) and Unsupervised (K-Means, PCA). Relies on explicit feature engineering.
- **Deep Learning**: Multi-layer neural networks (CNNs for vision, RNNs/Transformers for sequences) learning latent representations hierarchically.
- **Large Language Models (LLMs)**: Decoder-only autoregressive transformers (e.g., Llama, GPT) trained via next-token prediction on trillions of tokens.

## 2. Transformer Self-Attention Mechanism
The scaled dot-product attention computes relationships across all tokens in parallel:
$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{Q K^T}{\sqrt{d_k}}\right) V$$
- $Q$ (Query), $K$ (Key), $V$ (Value) are linear projections of input embeddings.
- $\sqrt{d_k}$ prevents gradients from vanishing in softmax when dimensionality is large.

## 3. Retrieval-Augmented Generation (RAG) Pipeline
Mitigates hallucinations by augmenting LLM prompts with verified external ground truth:
1. **Ingestion & Chunking**: Semantic splitting of knowledge corpus.
2. **Dense Vector Embeddings**: Generating embeddings via encoder models (e.g., `all-MiniLM-L6-v2`).
3. **Hybrid Retrieval**: Combining dense cosine similarity with sparse BM25/lexical token search.
4. **Reciprocal Rank Fusion (RRF)**: Merging multi-channel rankings robustly.
5. **Grounded Synthesis**: Feeding top evidence chunks strictly into system prompts.
