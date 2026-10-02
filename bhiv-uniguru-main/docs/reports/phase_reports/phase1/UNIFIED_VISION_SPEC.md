# UNIFIED_VISION_SPEC.md

## Purpose

This document defines the **technical target state** of Unified UniGuru.

It describes what the unified system must become once the unification project is complete.

This document does NOT describe timelines or progress.  
It defines the **final intended architecture and guarantees**.

---

## 1. Definition of Unified UniGuru

Unified UniGuru is a **deterministic, middleware-ready reasoning system** that safely integrates:

- Deterministic governance
- Deterministic rule-based reasoning
- Deterministic knowledge retrieval
- Generative RAG capabilities

Unified UniGuru is not a single model.  
It is a **layered execution pipeline**.

---

## 2. Target System Architecture

Final request pipeline:

User → Admission Layer → RLM Core → Retrieval Engine → Legacy Node RAG → Response

Each layer has a single responsibility.

---

## 3. Role of the RLM Middleware

The RLM Middleware sits **between the client and the legacy Node application**.

It performs:

- Governance enforcement
- Rule-based decision making
- Deterministic retrieval
- Safe forwarding of allowed requests

It acts as a **decision gate** in front of the generative system.

---

## 4. Deterministic Core Requirements

The RLM layer must guarantee:

- All decisions are rule-based
- No uncontrolled ML components are used
- Identical input produces identical decision paths
- Unsafe or prohibited requests never reach the LLM

This ensures predictable and auditable behavior.

---

## 5. Safe Delegation Model

Unified UniGuru must implement a **safe delegation pipeline**:

1. Validate request
2. Evaluate rules
3. Decide:
   - BLOCK
   - DIRECT ANSWER
   - FORWARD

The legacy generative system is only used when forwarding is approved.

---

## 6. Retrieval Role in Unified System

The retrieval engine must:

- Provide deterministic knowledge grounding
- Serve factual answers directly when possible
- Reduce reliance on generative responses
- Maintain a hierarchical knowledge base

Retrieval must occur **before any LLM call**.

---

## 7. Legacy System Role

The legacy Node/Express system remains responsible for:

- RAG pipeline execution
- LLM integration
- Conversational response generation
- Session-based interactions

It must remain:
- Unmodified
- Backwards compatible
- Replaceable

Unified UniGuru wraps the legacy system — it does not replace it.

---

## 8. Permanent Architectural Constraints

The following rules must always remain true:

1. No direct client access to `/chat`
2. Governance must occur before generation
3. Deterministic reasoning must precede retrieval and forwarding
4. Retrieval must precede LLM usage
5. Separation of concerns must be preserved

These constraints define the unified architecture.

---

## 9. Traceability Requirement

Every request must generate a traceable execution path including:

- Request receipt
- Rule evaluation results
- Retrieval actions
- Forwarding events
- Final response

This ensures full system observability.

---

## 10. Final Definition

Unified UniGuru is a **governed reasoning gateway** in front of a generative AI system.

RLM decides.  
Legacy Node generates.

Together they form the Unified UniGuru architecture.
