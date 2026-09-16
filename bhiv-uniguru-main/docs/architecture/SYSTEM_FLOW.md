# UniGuru System Flow Documentation

## 1. Execution Chain Diagram

```text
[ USER REQUEST ]
      |
      v
[ LAYER 1: API / INPUT LAYER ]
      | (Sanitization & Schema Validation)
      v
[ LAYER 2: GOVERNANCE PRE-CHECK ] ---> [ BLOCK ] (If "sudo", malicious, etc.)
      | (Safety Invariant Check)
      v
[ LAYER 3: RETRIEVAL LAYER ]
      | (Local KB Match in master_index.json)
      | (Optional: Verified Web Retrieval)
      v
[ LAYER 4: ONTOLOGY RESOLUTION ]
      | (Map result to concept_id & Domain)
      | (Graph Path Reasoning)
      v
[ LAYER 5: TRUTH VERIFICATION ]
      | (Source Audit: VERIFIED/PARTIAL/UNVERIFIED)
      v
[ LAYER 6: ENFORCEMENT LAYER ]
      | (Final Authority Lock & Sealing)
      v
[ LAYER 7: GOVERNANCE POST-AUDIT ] --> [ BLOCK ] (If output leaked authority)
      | (Action/Pattern Check)
      v
[ STRUCTURED REASONING RESPONSE ]
```

## 2. Layer Definitions

### Layer 1 — API / Input Layer
Receives the raw JSON payload (`user_query`). Ensures clean service boundaries and extracts parameters like `allow_web_retrieval`.

### Layer 2 — Governance Layer (Pre-Check)
Scans user input for malicious patterns (e.g., code injection, system commands) and classifies intent.

### Layer 3 — Retrieval Layer
Uses the `KnowledgeRetriever` to pull ground truth from the physical filesystem. If enabled, performs search-and-verify against allowed web domains.

### Layer 4 — Ontology Resolution
Anchors the retrieved data to the UniGuru Ontology Backbone. It identifies the `concept_id`, `version`, and calculates the `reasoning_path` from the domain root.

### Layer 5 — Truth Verification
Assigns a truth level and status to the response. Only `VERIFIED` or `PARTIAL` results are allowed to proceed. `UNVERIFIED` results trigger a fail-closed refusal.

### Layer 6 — Enforcement Layer
The final gatekeeper. It cryptographically binds the decision and ensures the response is sealed with a signature.

### Layer 7 — Output Governance (Post-Audit)
Performs a final audit of the generated string to ensure no system actions or executive authority patterns are leaked to the user.

## 3. Reasoning Trace Components
Every successful response must include:
- **Ontology Reference**: Proof of grounding in the registry.
- **Sources Consulted**: Traceability to physical files or URLs.
- **Confidence Score**: Deterministic overlap calculation.
- **Verification Status**: Clear declaration of truth status.


## Merged: backend/uniguru/GOVERNANCE_EXPLANATION.md

# UniGuru Governance: The Invariant Layer

## 1. What is the Governance Layer?
Governance is the system's "conscience." It is a dedicated layer that enforces high-level policies (Safety, Legality, Ethics, and Technical Invariants) that the Logic layer might overlook.

## 2. Why It Must Exist
In a complex system, the Logic layer is busy deciding "How to answer." The Governance layer is a watchdog that asks "Should we be answering at all?" or "Is the answer leaking secrets?" Without a separate governance layer, the system is vulnerable to **Prompt Injection** and **Logic Bypass**.

## 3. Pre-Logic vs. Post-Logic Governance
UniGuru implements a "Governance Sandwich":
*   **Pre-Logic**: Filters incoming user messages. It catches malicious strings *before* the reasoning engine even sees them.
*   **Post-Logic**: Audits the generated response *after* logic is finished but *before* the user sees it. This catches sensitive leaks.

## 4. Rule Example: Blocking "Hack exam"
A rule in the governance engine looks for prohibited keyword combinations.
*   **Pattern**: `r"(hack|cheat|exam answers)"`
*   **Action**: Immediately return `SafetyStatus.DENIED`.
*   **Reason**: Academic Integrity violation.

## 5. Deterministic Rule Engine
The engine uses **Regular Expressions (Regex)**. Unlike an "AI filter" that might be tricked by polite language, a Regex rule is binary:
*   Does "sudo" exist in the string?
*   Yes → Block.
*   No → Pass.
This removes the "Grey area" that attackers exploit.

## 6. Failure Scenarios
*   **False Positive**: A user asking "How to prevent a hack?" might be blocked because the word "hack" is forbidden.
*   **Obfuscation**: An attacker typing `h.a.c.k` might bypass a simple regex.

## 7. Production Hardening Strategies
1.  **Regex Complexity**: Use boundary markers (`\bhack\b`) to avoid blocking words like "shack."
2.  **Frequency Analysis**: Block users who repeatedly trigger governance.
3.  **Audit Logs**: Every governance block must be logged with the raw input for manual review.
