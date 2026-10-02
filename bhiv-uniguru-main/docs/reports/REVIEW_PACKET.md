# REVIEW_PACKET.md

DO NOT USE FOR CURRENT INTEGRATION.
Use root `REVIEW_PACKET.md` for the canonical integration-aware review.

## 1. ENTRY POINT

**Frontend entry:**
Path: `Complete-Uniguru/frontend/src/main.tsx`

**Backend entry:**
Path: `uniguru/service/api.py`

**Explain in 2 lines:**
The system starts with a user query from the React-based frontend hitting the FastAPI `/ask` endpoint, which triggers the reasoning and routing pipeline.

---

## 2. CORE EXECUTION FLOW (MAX 3 FILES ONLY)

**File 1: Router / Decision Layer**
Path: `uniguru/router/conversation_router.py`
**What it does:** Classifies queries into Knowledge, System, or Workflow types and routes them to the correct engine while blocking unsafe system-level commands.

**File 2: API Layer**
Path: `uniguru/service/api.py`
**What it does:** Manages the FastAPI server, request validation (Pydantic), caller authentication, and acts as the orchestration hub for STT, Router, and Telemetry.

**File 3: Execution Layer (KB / LLM / Workflow)**
Path: `uniguru/core/engine.py`
**What it does:** Performs deterministic retrieval from the local Knowledge Base (KB) using RuleEngine logic to ensure responses are grounded in verified ontology snapshots.

---

## 3. LIVE FLOW (REAL EXECUTION)

**User action:**
User asks: “What is a qubit?”

**System flow:**
Frontend → API → Router → Engine → Response

**REAL RESPONSE:**
```json
{
  "decision": "answer",
  "answer": "Based on verified source: qubit.md\n\nUniGuru Deterministic Knowledge Retrieval:\n\nTitle: Nielsen & Chuang Core Concepts\nSource(s): Nielsen, M. A. & Chuang, I. L., \"Quantum Computation and Quantum Information\" (2010)\nAuthors: Michael A. Nielsen; Isaac L. Chuang (summarized)\nYear: 2010\nDomain: Quantum Foundations / Quantum Information\nIngestion date: 2026-02-06\n\nDefinitions\n- Qubit: Two-level quantum system represented by state vector |ψ⟩=α|0⟩+β|1⟩.\n- Density operator: ρ describing mixed states; ρ=∑i pi|ψi⟩⟨ψi|.\n- Unitary evolution: Closed-system dynamics described by ρ↦UρU†.\n- Measurement (projective): Born rule pi=⟨ψ|Πi|ψ⟩ for projector Πi.\n- Entanglement: Non-separable joint states with correlations beyond classical mixtures.\n\nKey Concepts\n- State space: Hilbert space formalism and tensor-product composition.\n- Quantum gates: Reversible operations implemented by unitary matrices.\n- Quantum circuits: Composition of gates to implement algorithms.\n- Quantum error: Decoherence and noise motivating error correction.\n\nLight equation context\n- State normalization: ⟨ψ|ψ⟩=1.\n- Expectation value: ⟨A⟩=Tr(ρA).\n\nConcept explanations\n- Superposition: Linear combination of basis states enabling interference.\n- Measurement collapse (operational): Probabilistic update of state post-measurement.\n- Quantum tomography (summary): Reconstruction of ρ from measurement statistics.\n\nCitations\n- Nielsen & Chuang (2010). Core textbook treatment of these foundational topics.",
  "session_id": null,
  "reason": "Knowledge found in local KB and verified.",
  "ontology_reference": {
    "concept_id": "2200072c-5a0d-4f68-a56a-a0c807f6cf5e",
    "domain": "quantum",
    "snapshot_version": 1,
    "snapshot_hash": "e7292c6b78cfa8c7fe0008b36f6916879af5b9c78d763a3cbf402d3e3d6895ad",
    "truth_level": 3
  },
  "reasoning_trace": {
    "sources_consulted": [
      "ontology_graph",
      "ontology_registry",
      "quantum"
    ],
    "retrieval_confidence": 1.0,
    "ontology_domain": "quantum",
    "verification_status": "VERIFIED",
    "verification_details": "VERIFIED"
  },
  "governance_flags": {
    "safety": false
  },
  "governance_output": {
    "allowed": true,
    "reason": "Output governance passed.",
    "flags": {
      "output_authority_violation": false
    }
  },
  "verification_status": "VERIFIED",
  "status_action": "ALLOW",
  "enforcement_signature": "d34e82bb0bf8d9950ac01051c2817a1d0ecd3cae64c97846124e9d1ef148e71e",
  "request_id": "31fc727b-a607-4cef-b5c0-905b15c4a7da",
  "sealed_at": "2026-03-10T03:21:54Z",
  "latency_ms": 10.25
}
```

---

## 4. WHAT WAS BUILT IN THIS TASK

• Added: REVIEW_PACKET.md extraction for system clarity.
• Modified: None.
• Not touched: Router logic, API infrastructure, Reasoning engine, STT pipeline.

---

## 5. FAILURE CASES

• **If backend fails:** Returns a TCP connection error or 503 Service Unavailable if any component is unresponsive.
• **If invalid input:** API returns 422 Unprocessable Entity due to Pydantic schema validation failure.
• **If router blocks:** Returns a `decision: block` response with reason "System command blocked by router policy."

---

## 6. PROOF

**API Response Log Snippet:**
```
INFO:uniguru.service.api:{"event": "request_processed", "service": "uniguru-live-reasoning", "caller_name": "internal-testing", "decision": "answer", "latency": 10.25, "query_hash": "a8f1...", "route": "ROUTE_UNIGURU", "verification_status": "VERIFIED"}
```
*(Extracted from `integration_test_evidence.json` and service logs)*
