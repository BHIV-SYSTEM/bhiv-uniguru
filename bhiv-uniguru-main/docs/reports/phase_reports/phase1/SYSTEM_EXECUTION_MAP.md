# SYSTEM_EXECUTION_MAP.md

## Purpose

This document defines the complete execution chain of Unified UniGuru from user input to final response.

It exists so that a new engineer can reconstruct the system without prior knowledge.

This document removes ambiguity around:
- Execution order
- System boundaries
- Decision gates
- Deterministic vs generative layers

---

## 1. System Overview

Unified UniGuru is a layered decision pipeline combining:

| Layer | Type | Role |
|---|---|---|
| Admission Middleware | Deterministic | Request governance |
| RLM Core | Deterministic | Rule-based reasoning |
| Retrieval Engine | Deterministic | Knowledge grounding |
| Legacy Node UniGuru | Generative | Production RAG + chat |

The architecture intentionally separates:
- Governance
- Reasoning
- Retrieval
- Generation

This prevents authority leakage and enables safe evolution.

---

## 2. High-Level Execution Pipeline

Client → Admission → Rule Engine → Retrieval → Legacy RAG → Response

Every request MUST pass through this pipeline.  
No direct access to the legacy system is allowed.

---

## 3. Step-by-Step Execution Flow

### Step 1 — Client Request

User sends HTTP request:

POST /admit

Payload:
```json
{
  "message": "string",
  "session_id": "string",
  "source": "string"
}
This is the only public entry point.
Step 2 — Admission Middleware

Responsibilities:

Validate request contract

Generate trace_id

Log request receipt

Pass request to RLM rule engine

Admission Decision Gate
Outcome	Result
Reject	HTTP 400 returned
Allow	Forward to RLM core

Rejected requests terminate here.

Step 3 — RLM Rule Engine (Deterministic Reasoning)

The Rule Engine evaluates requests in fixed priority order:

AuthorityRule

UnsafeRule

AmbiguityRule

EmotionalRule

DelegationRule

This order never changes.

Possible Outcomes
Decision	Meaning
BLOCK	Unsafe or invalid request
DIRECT_ANSWER	Answer from KB only
FORWARD	Send to legacy Node RAG

This is the primary decision layer of Unified UniGuru.

Step 4 — Retrieval Engine

Triggered only for:
DIRECT_ANSWER

Retrieval pipeline:
Query → Keyword Resolver → File Mapping → Context Assembly

Retrieval Hierarchy

Foundations KB

Domain KB

General KB

This ensures deterministic knowledge grounding.

Step 5 — Legacy Node UniGuru (Generative Layer)

Triggered only for:
FORWARD

Endpoint:
POST /chat

Responsibilities:

Execute existing RAG pipeline

Call LLM

Generate final response

⚠️ This layer is unchanged production code.

Step 6 — Response Return Flow

Legacy → Middleware → Client

Middleware attaches:

trace_id

logs

deterministic response contract

Example:

{
  "trace_id": "uuid",
  "data": {
    "answer": "Generated response"
  }
}

4. System Boundary Definition
Boundary	Purpose
Admission ↔ RLM	Governance separation
RLM ↔ Retrieval	Reasoning vs Knowledge
Retrieval ↔ Legacy	Deterministic vs Generative

No layer bypass is permitted.

5. Determinism Guarantee

Determinism enforced via:

Pure rule functions

Fixed rule priority

Fixed retrieval hierarchy

Structured response contract

No uncontrolled ML components

Same input → Same decision path → Same outcome.

6. Observability & Traceability

Each request includes a trace_id.

Logs capture:

Request received

Rule decisions

Retrieval execution

Forwarding events

Final response

Full execution trace is reproducible.

7. Final Summary

Unified UniGuru now operates as a controlled reasoning gateway in front of the legacy RAG system.

User → Governance → Reasoning → Retrieval → Generation → Response

This architecture enables safe, deterministic evolution of UniGuru.