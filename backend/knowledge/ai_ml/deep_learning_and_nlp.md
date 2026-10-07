---
title: Deep Learning Architectures, Neural Networks, and NLP
domain: ai_ml
subject: Deep Learning & NLP
authority_score: 0.99
source_name: PyTorch Documentation & Deep Learning Book (Goodfellow, Bengio, Courville)
source_url: https://pytorch.org/docs/
license: Open Source / Educational
verification_status: VERIFIED
last_verified: 2026-10-02
---

# Deep Learning Architectures, Neural Networks, and NLP

## 1. Deep Neural Networks & Backpropagation
A Multi-Layer Perceptron (MLP) consists of stacked layers of parameterized linear transformations and non-linear activation functions:
$$\mathbf{h}^{(l)} = \sigma\left(\mathbf{W}^{(l)} \mathbf{h}^{(l-1)} + \mathbf{b}^{(l)}\right)$$
- **Activation Functions**:
  - **ReLU**: $\max(0, x)$. Mitigates vanishing gradient in deep layers.
  - **GELU**: $x \cdot \Phi(x)$. Standard in modern Transformers.
  - **Softmax**: Normalizes logits into probability distributions $\sigma(\mathbf{z})_i = \frac{e^{z_i}}{\sum_j e^{z_j}}$.
- **Backpropagation**:
  Computes the gradient of the scalar loss $L$ with respect to every weight tensor $\mathbf{W}$ via recursive application of the calculus **Chain Rule**:
  $$\frac{\partial L}{\partial \mathbf{W}^{(l)}} = \frac{\partial L}{\partial \mathbf{h}^{(l)}} \frac{\partial \mathbf{h}^{(l)}}{\partial \mathbf{z}^{(l)}} \frac{\partial \mathbf{z}^{(l)}}{\partial \mathbf{W}^{(l)}}$$
- **Optimizers**: SGD with Momentum, RMSprop, and **AdamW** (Adaptive Moment Estimation with decoupled weight decay).

## 2. Computer Vision & Convolutional Neural Networks (CNNs)
- **Convolution Layer**: Slides spatial kernels across multi-channel feature maps, enforcing translation equivariance and parameter sharing.
- **Pooling**: Max pooling downsamples feature dimensions, introducing spatial translation invariance.
- **Classic Architectures**: ResNet (Residual Networks with identity skip connections $\mathbf{y} = \mathcal{F}(\mathbf{x}) + \mathbf{x}$ enabling training of 100+ layer networks without vanishing gradients).

## 3. Natural Language Processing (NLP) & Sequence Modeling
- **Tokenization**:
  - Subword tokenization (Byte-Pair Encoding / BPE, WordPiece, SentencePiece) eliminates out-of-vocabulary (OOV) errors while keeping vocabulary sizes bounded ($\sim 32\text{k}\text{ - }128\text{k}$).
- **Recurrent Architectures**:
  - **RNN**: Sequential updates $h_t = \tanh(W x_t + U h_{t-1})$; suffers from vanishing/exploding gradients over long contexts.
  - **LSTM & GRU**: Introduce input, forget, and output gating mechanisms with linear cell state highways to preserve long-range dependencies.
- **Word Embeddings**:
  Dense vector representations where semantic relationships map to vector arithmetic (Word2Vec Skip-gram, GloVe).
