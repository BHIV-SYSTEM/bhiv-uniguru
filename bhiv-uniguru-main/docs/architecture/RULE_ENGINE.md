# REASONING_ENGINE_ARCHITECTURE

## Overview
UniGuru now includes deterministic ontology reasoning modules under `uniguru/reasoning/`:
- `concept_resolver.py`
- `graph_reasoner.py`
- `reasoning_trace.py`

No ML/LLM/embedding/vector behavior is used.

## 1) Concept Resolver
File: `uniguru/reasoning/concept_resolver.py`

Input:
- user query
- retrieval trace

Output (contract):
- `concept_id`
- `canonical_name`
- `domain`
- `truth_level`
- `snapshot_version`
- `snapshot_hash`

Behavior:
- deterministic domain resolution from retrieval trace and strict token map
- deterministic concept match by canonical-name token overlap
- deterministic fallback to domain concept or unresolved concept

## 2) Graph Traversal Reasoning
File: `uniguru/reasoning/graph_reasoner.py`

Behavior:
- builds ontology adjacency deterministically from snapshot
- computes shortest path with BFS
- supports domain-root reasoning path generation

Example chain:
- `Qubit -> Superposition -> Entanglement -> Quantum Algorithms` (when traversing deeper ontology path)

## 3) Reasoning Trace Design
File: `uniguru/reasoning/reasoning_trace.py`

Trace schema:
- `concept_chain`
- `truth_levels`
- `snapshot_version`
- `snapshot_hash`

Example:
```json
{
  "concept_chain": ["quantum root", "qubit"],
  "truth_levels": [4, 3],
  "snapshot_version": 1,
  "snapshot_hash": "e7292c6b78cfa8c7fe0008b36f6916879af5b9c78d763a3cbf402d3e3d6895ad"
}
```

## Engine Integration
File: `uniguru/core/engine.py`

Runtime chain:
- Input
- Governance
- Retrieval
- Source Verification
- Concept Resolution
- Ontology Reasoning
- Enforcement
- Response

Reasoning execution condition:
- runs only when retrieval succeeds (`decision=answer` and `retrieval_trace.match_found=true`).


## Merged: backend/uniguru/RULE_MATRIX.md

# UniGuru Deterministic Rule Matrix

This document defines the formal rules used by the UniGuru Reasoning Layer to classify and respond to user queries.

| Rule ID | Name | Trigger Condition | Detection Layer | Decision Output | Enforcement Override |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **UG-001** | **SafetyRule** | Verboten patterns (sudo, rm -rf, SQLi, hack) | Enforcement/Safety | **BLOCK** | Always |
| **UG-002** | **AuthorityRule** | Power dynamic detection (Boss, Teacher) + Coercion terms | Governance/Authority | **BLOCK** if Severity > 0.5 | If Severity > 0.8 |
| **UG-003** | **DelegationRule** | Responsibility transfer (Academic, Technical, Legal) | Governance/Delegation | **BLOCK** | Always |
| **UG-004** | **EmotionalRule** | Distress, Urgency, Hostility, Confusion triggers | Governance/Emotional | **ANSWER** (De-escalation) | Context Dependent |
| **UG-005** | **AmbiguityRule** | Semantic/Contextual/Incomplete query patterns | Governance/Ambiguity | **ANSWER** (Clarification) | Never |
| **UG-006** | **RetrievalRule** | Keyword match in `Quantum_KB` | Core/Retrieval | **ANSWER** (Grounded) | Output Audit |
| **UG-007** | **ForwardRule** | No specific trigger (Catch-all) | Core/Forward | **FORWARD** (Legacy/Human) | Audit Required |

## Detection Definitions

### Ambiguity Classes
- **INCOMPLETE**: Tokens <= 1.
- **CONTEXTUAL**: Only vague pronouns (e.g., "What about that?").
- **SEMANTIC**: Vague action + vague pronoun (e.g., "Do it").

### Delegation Categories
- **ACADEMIC**: Requests to solve exams or homework.
- **TECHNICAL**: Requests for system execution or automation.
- **LEGAL/ETHICAL**: Requests for the system to make binding decisions.

### Power Dynamics
- **TECHNICAL**: Sudo/Root impersonation attempts.
- **PROFESSIONAL**: Using workplace authority to bypass rules.
- **ACADEMIC**: Using institutional authority.
- **PERSONAL**: Emotional manipulation or trust-based pressure.

### Emotional Matrix
- **DISTRESS**: Signals of being overwhelmed or unable to cope.
- **URGENCY**: High-speed demands (ASAP).
- **HOSTILITY**: Aggressive or critical behavior.
- **CONFUSION**: Explicit statements of being lost.
