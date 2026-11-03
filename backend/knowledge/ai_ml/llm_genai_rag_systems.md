---
title: Large Language Models, Generative AI, and RAG Architecture
domain: ai_ml
subject: LLMs & Generative AI
authority_score: 0.99
source_name: Vaswani et al. (2017) & Lewis et al. (2020) RAG Paper (arXiv:2005.11401)
source_url: https://arxiv.org/abs/2005.11401
license: Open Academic Access
verification_status: VERIFIED
last_verified: 2026-10-02
---

# Large Language Models, Generative AI, and RAG Architecture

## 1. Transformer Architecture & Self-Attention
Introduced in *"Attention Is All You Need"* (Vaswani et al., 2017), the Transformer eliminates recurrent connections in favor of global parallel attention:
- **Scaled Dot-Product Attention**:
  $$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{Q K^T}{\sqrt{d_k}}\right) V$$
  where queries $Q$, keys $K$, and values $V$ are linear projections of input embeddings.
- **Multi-Head Attention (MHA)**:
  Projects queries, keys, and values into $h$ distinct representation subspaces, enabling the model to attend simultaneously to syntactic, semantic, and positional contexts.
- **Decoder-Only LLMs (GPT, LLaMA, Mistral)**:
  Autoregressive language modeling with causal attention masks preventing tokens from attending to subsequent future tokens.

## 2. Advanced Retrieval-Augmented Generation (RAG)
RAG mitigates hallucinations and enables dynamic factual updates by anchoring model responses in authoritative retrieved evidence:
- **Dense Vector Search**:
  Encodes text chunks into high-dimensional vector spaces (e.g. 384-d, 768-d, 1536-d) and conducts Nearest Neighbor Search using Index Flat Inner Product or Hierarchical Navigable Small World (HNSW) graphs.
- **Hybrid Retrieval (Vector + BM25)**:
  Combines semantic similarity (dense embeddings) with exact keyword matching (BM25 / SQLite FTS5) via **Reciprocal Rank Fusion (RRF)**:
  $$\text{RRF\_Score}(d) = \sum_{m \in M} \frac{1}{k + r_m(d)} \quad (\text{typically } k = 60)$$
- **Reranking**:
  Passes candidate chunks through a cross-encoder model to compute fine-grained relevance scores between the query and each chunk, selecting only the top-k highest quality chunks.

## 3. Post-Training: Fine-Tuning, LoRA, and LLM Alignment
- **Instruction Tuning (SFT)**: Fine-tunes pretrained base models on structured prompt-response pairs.
- **Parameter-Efficient Fine-Tuning (PEFT) & LoRA**:
  Instead of updating all billions of weights $W_0$, Low-Rank Adaptation (LoRA) freezes $W_0$ and trains low-rank matrix decomposition adapters:
  $$W = W_0 + \Delta W = W_0 + B A \quad \text{where } B \in \mathbb{R}^{d \times r}, A \in \mathbb{R}^{r \times k}, r \ll \min(d, k)$$
- **Quantization (4-bit / 8-bit)**:
  Compresses weight representations (e.g. FP16 $\to$ INT4 via AWQ, GPTQ, GGUF) reducing VRAM consumption by 75% with minimal perplexity degradation.
