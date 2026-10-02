# Retrieval Trace Log Specification (V2)

## 1. Objective
Provide a forensic, deterministic audit trail for every knowledge base retrieval operation. This ensures that the reasoning behind file selection is transparent and reproducible.

## 2. Trace Schema

Every retrieval operation MUST generate a `RetrievalTrace` object as part of the system response.

```json
{
  "retrieval_trace_id": "uuid",
  "timestamp": "iso-8601",
  "query": {
    "original": "string",
    "normalized": "string",
    "tokens": ["list", "of", "keywords"]
  },
  "scoring": [
    {
      "file": "path/to/file.md",
      "matches": ["keyword1", "keyword2"],
      "score": 2.5,
      "tier": "foundations | domain | general"
    }
  ],
  "final_selection": {
    "files": ["list", "of", "selected", "files"],
    "fallback_triggered": false,
    "total_kb_words": 1250
  }
}
```

## 3. Log Components

### A. Normalization Trace
Records how the input query was sanitized:
- **Lowercase Conversion**: TRUE
- **Punctuation Stripped**: TRUE
- **Stopwords Removed**: List of removed tokens (e.g., "what", "is", "a").

### B. Scoring Breakdown
For every file that matched at least one keyword, the log must show:
- **Match Count**: Number of unique query keywords found in the filename or content headers.
- **Path Weight**: Higher weights for files in the `Foundations` tier (root level) vs `Domain` (subdirectories).
- **Final Score**: The deterministic value used for ranking.

### C. Hierarchy Resolution
Indicates which tier of the fallback hierarchy was used:
1.  **Tier 1 (Foundations)**: Root-level core concepts (Qubit, Superposition).
2.  **Tier 2 (Domain)**: Specialized subdirectories (Quantum_Algorithms, Quantum_Physics).
3.  **Tier 3 (General)**: Catch-all index or overview files.

## 4. Determinism Guarantee
The trace ID must be linked to the `request_id`. For identical inputs, the `scoring` array MUST be identical in content and order.

## 5. Storage
Retrieval traces are included in the API response and logged to the central `admission.log` (or dedicated `retrieval.log`) for offline audit.
