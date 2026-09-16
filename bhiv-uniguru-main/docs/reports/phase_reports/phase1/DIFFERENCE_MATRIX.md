# DIFFERENCE_MATRIX.md

## Purpose

This document compares the **Python UniGuru (Deterministic RLM Core)** and the **Legacy Node UniGuru (Generative RAG System)**.

This fulfills the requirement:
Compare Python UniGuru vs Node UniGuru.

The goal is to clearly show:
- What exists today
- What each system does well
- Why both must be unified
- How responsibilities differ

---

## 1. High-Level Comparison

| Category | Python UniGuru (RLM Core) | Legacy Node UniGuru |
|---|---|---|
| Primary Role | Deterministic reasoning | Generative chat + RAG |
| Determinism | ✔ Yes | ❌ No |
| LLM Usage | ❌ None | ✔ Yes |
| Retrieval Type | Keyword KB | Vector DB |
| State | Stateless | Session-based |
| Safety Layer | ✔ Rule engine | ❌ None |
| Production Capability | Demo-safe | Full product |

These systems are complementary, not competing.

---

## 2. Architectural Purpose

### Python UniGuru (RLM Core)

Designed for:
- Governance
- Safety
- Deterministic decision making
- Knowledge grounding

Acts as a **Decision Engine**.

---

### Legacy Node UniGuru

Designed for:
- Conversational AI
- RAG pipeline
- Session chat
- LLM generation

Acts as a **Generative Engine**.

---

## 3. Input Handling

| Aspect | Python RLM | Node Legacy |
|---|---|---|
| Request validation | ✔ Strict | ❌ Minimal |
| Payload contract | ✔ Enforced | ❌ Flexible |
| Traceability | ✔ trace_id | ❌ None |
| Safety checks | ✔ Yes | ❌ None |

The Python system protects the Node system.

---

## 4. Decision Capability

| Capability | Python RLM | Node Legacy |
|---|---|---|
| Block unsafe requests | ✔ Yes | ❌ No |
| Detect ambiguity | ✔ Yes | ❌ No |
| Emotional handling | ✔ Yes | ❌ No |
| Delegation refusal | ✔ Yes | ❌ No |
| Direct KB answers | ✔ Yes | ❌ No |

The Node system assumes all input is safe.

---

## 5. Retrieval Comparison

| Feature | Deterministic KB | Vector DB |
|---|---|---|
| Deterministic | ✔ Yes | ❌ No |
| Auditable | ✔ Yes | ❌ Limited |
| Expandable | ✔ Yes | ✔ Yes |
| Semantic search | ❌ No | ✔ Yes |
| Hallucination risk | Low | Medium |

Both retrieval systems are required.

---

## 6. Response Generation

| Feature | Python RLM | Node Legacy |
|---|---|---|
| Generates text | ❌ No | ✔ Yes |
| Uses LLM | ❌ No | ✔ Yes |
| Conversational memory | ❌ No | ✔ Yes |
| Creativity | ❌ No | ✔ Yes |

Generation must remain in Node.

---

## 7. Why Unification Is Required

Without unification:
- Unsafe queries reach LLM directly
- No governance layer exists
- No deterministic reasoning exists
- No traceability exists

With unification:
Python → decides  
Node → generates

This is the core architecture principle.

---

## 8. Target Unified Model

Unified UniGuru combines both:

Python RLM → Governance + Reasoning  
Node UniGuru → Generation + RAG  

Final pipeline:

Client → Middleware → RLM → Retrieval → Node → Response

---

## 9. Summary

The two systems serve different but complementary roles:

Python UniGuru = Brain (Decision Engine)  
Node UniGuru = Voice (Generative Engine)

Unification combines **determinism + generation** into a single safe architecture.
