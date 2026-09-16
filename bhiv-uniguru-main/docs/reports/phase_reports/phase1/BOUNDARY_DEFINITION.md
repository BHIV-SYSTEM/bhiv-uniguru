# BOUNDARY_DEFINITION.md

## Purpose

This document defines the governance, enforcement, reasoning, retrieval, and generation boundaries of Unified UniGuru.

The goal is to guarantee:
- No authority leakage between layers
- No accidental bypass of safety rules
- Clear separation of responsibilities
- Safe future integration across the BHIV ecosystem

This document acts as the system’s separation-of-concerns contract.

---

## 1. Boundary Philosophy

Unified UniGuru intentionally separates the system into strict execution zones:

Governance → Reasoning → Knowledge → Generation

Each zone has:
- Exclusive responsibilities
- Explicit prohibitions
- Strict data contracts

No layer may perform another layer’s role.

---

## 2. Layer Overview

| Layer | Role | Type |
|---|---|---|
| Admission Layer | Request governance | Deterministic |
| RLM Core | Rule-based reasoning | Deterministic |
| Retrieval Engine | Knowledge grounding | Deterministic |
| Legacy Node UniGuru | RAG + LLM generation | Non-deterministic |

This separation ensures safe evolution and backward compatibility.

---

## 3. Governance Boundary (Admission Layer)

### Responsibilities
The Admission Layer is the only public entry point.

It is responsible for:
- Request contract validation
- Payload size limits
- JSON structure validation
- Trace ID generation
- Early rejection of unsafe input

It answers the question:
Should this request enter the UniGuru system?

### Prohibited Actions
The Admission Layer must never:
- Perform reasoning
- Access the knowledge base
- Call LLM providers
- Modify business payloads
- Implement product logic

It is strictly a request gatekeeper.

---

## 4. Reasoning Boundary (RLM Core)

The RLM Core is the deterministic decision engine.

It answers the question:
How should UniGuru respond?

### Responsibilities
- Evaluate rule classes
- Decide BLOCK / DIRECT_ANSWER / FORWARD
- Trigger retrieval when appropriate
- Prevent unsafe requests from reaching LLMs

### Prohibited Actions
The RLM Core must never:
- Accept external requests directly
- Generate LLM responses
- Access production secrets
- Modify legacy Node code

---

## 5. Knowledge Boundary (Retrieval Engine)

The Retrieval Engine is knowledge-only.

It answers:
What verified information exists?

### Responsibilities
- Keyword resolution
- Knowledge base file lookup
- Context assembly
- Deterministic content retrieval

### Prohibited Actions
The Retrieval Engine must never:
- Apply rules or make decisions
- Call LLMs
- Modify queries
- Perform generation

This keeps retrieval fully deterministic.

---

## 6. Generation Boundary (Legacy Node UniGuru)

This layer provides existing production capabilities.

It answers:
How should the response be generated?

### Responsibilities
- Execute RAG pipeline
- Call LLM providers
- Generate conversational responses
- Maintain backward compatibility

### Critical Constraint
This layer must remain:
- Unmodified
- Replaceable
- Isolated from governance logic

---

## 7. Governance Invariants

These rules are system-wide and non-negotiable.

Authority Invariant  
The system must never override its own rules.

Safety Invariant  
Unsafe or prohibited content must never reach the LLM.

Ambiguity Invariant  
The system must never guess unclear intent.

Delegation Invariant  
The system must never perform academic or professional work on behalf of the user.

Emotional Boundary  
The system may acknowledge distress but must never provide therapy or counseling.

---

## 8. Rule Enforcement Order

Rules must execute in fixed priority:

1. Unsafe / Prohibited → BLOCK
2. Authority Challenge → BLOCK
3. Ambiguity → CLARIFY
4. Emotional Load → REDIRECT
5. Delegation Request → REFUSE / GUIDE
6. Factual Query → RETRIEVE
7. General Conversation → FORWARD

The order is deterministic and immutable.

---

## 9. Inter-Layer Data Contracts

| From | To | Contract |
|---|---|---|
| Admission | RLM | Validated request + trace_id |
| RLM | Retrieval | Clean query string |
| RLM | Legacy Node | Forwarded request payload |
| Legacy Node | Client | Generated response + trace_id |

Contracts prevent hidden coupling.

---

## 10. Why These Boundaries Matter

These separations allow:
- Middleware insertion
- Retrieval upgrades
- Rule engine expansion
- Future replacement of legacy Node

Without breaking production behavior.

---

## 11. Summary

Unified UniGuru enforces strict separation:

Governance → Reasoning → Knowledge → Generation

This boundary model ensures:
- Determinism
- Safety
- Replaceability
- Long-term scalability
