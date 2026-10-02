# RLM_V1_SPEC.md

## Purpose

This document defines the **Rule-Based Language Model (RLM v1)** used by Unified UniGuru.

RLM v1 is a deterministic reasoning system that evaluates every request before any generative model is used.

This specification defines:
- Scope
- Capabilities
- Constraints
- Expected behavior

This is a design specification, not an implementation report.

---

## 1. Definition of RLM v1

RLM v1 is a **deterministic rule engine** that sits between the user and the generative system.

It evaluates user input and decides whether to:

- BLOCK the request
- ANSWER deterministically
- FORWARD the request to the legacy generative system

RLM v1 ensures governance and safety.

---

## 2. System Scope

RLM v1 replaces:
- Ad-hoc rule checks
- Unstructured keyword filtering
- Direct access to LLM systems

RLM v1 introduces:
- Rule classes
- Deterministic evaluation order
- Execution tracing
- Governance enforcement

---

## 3. Core Architecture

Expected module structure:

core/
engine.py
rules/
base.py
safety.py
authority.py
delegation.py
emotional.py
ambiguity.py
retrieval.py
forward.py

Each rule is implemented as a deterministic class.

---

## 4. RLM Decision Pipeline

Execution pipeline:

1. Receive validated request
2. Create RuleContext
3. Execute rules in priority order
4. Stop at first terminal decision
5. Return structured response

---

## 5. Supported Rule Categories

| Category | Purpose |
|---|---|
| UnsafeRule | Detect harmful or prohibited input |
| AuthorityRule | Prevent rule override attempts |
| DelegationRule | Prevent performing work for user |
| EmotionalRule | Detect emotional distress |
| AmbiguityRule | Detect unclear queries |
| RetrievalRule | Provide deterministic KB answers |
| ForwardRule | Delegate safe queries to legacy system |

These categories define RLM v1 behavior.

---

## 6. Deterministic Guarantees

RLM v1 must guarantee:

- Pure rule functions
- No external API calls
- No randomness
- Fixed rule order
- Single terminal decision per request

Same input → Same decision path → Same result.

---

## 7. Decision Outputs

Every request must result in one of:

| Action | Meaning |
|---|---|
| BLOCK | Request rejected |
| ANSWER | Deterministic response returned |
| FORWARD | Sent to legacy generative system |

No other outcomes are permitted.

---

## 8. Traceability Requirements

Every decision must produce a trace containing:

- Request ID
- Rules executed
- Final decision

This enables observability and debugging.

---

## 9. Safety Guarantee

RLM v1 must ensure:

Unsafe or prohibited requests never reach the generative system.

This is the primary responsibility of the RLM.

---

## 10. Role in Unified Architecture

RLM v1 sits between:

Admission Layer → RLM → Retrieval → Legacy Node

It acts as the **deterministic reasoning gateway**.

---

## 11. Summary

RLM v1 transforms UniGuru into a **governed reasoning system**.

It ensures:
- Determinism
- Safety
- Traceability
- Controlled delegation to generative AI
