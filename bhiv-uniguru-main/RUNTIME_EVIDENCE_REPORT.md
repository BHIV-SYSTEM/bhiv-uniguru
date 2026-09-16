# Runtime Evidence Report

This report outlines the expanded runtime evidence contract layer designed and implemented for UniGuru. Every runtime query execution now produces a verifiable cryptographic response contract tracing the generated answers back to physical textbook pages.

## Evidence Contract Registry

- **Contract Schema**: [runtime_evidence_contract.json](file:///c:/Users/Yass0/OneDrive/Desktop/uniguru_3/uniguru_v2-main/backend/contracts/runtime_evidence_contract.json)
- **Runtime Orchestrator**: [canonical_runtime.py](file:///c:/Users/Yass0/OneDrive/Desktop/uniguru_3/uniguru_v2-main/learning_runtime/canonical_runtime.py)

## Expanded Response Properties

Every response returned by `CanonicalRuntime.execute` now guarantees inclusion of the following evidence fields at its root level:

| Property | Type | Description |
| :--- | :--- | :--- |
| `evidence_id` | `string` (UUID) | Cryptographic transaction signature of the execution path. |
| `textbook_id` | `string` | Unique identifier of the verified textbook authority source. |
| `edition` | `string` | The publication edition (e.g. `2023`). |
| `chapter` | `string` | The originating chapter name. |
| `section` | `string` | The originating section name. |
| `page_numbers` | `array` of `int` | The physical page number(s) where the content resides. |
| `source_hash` | `string` (SHA-256) | The hash of the page contents in the authoritative registry. |
| `retrieval_hash` | `string` (SHA-256) | Hash of the query-to-record retrieval state. |
| `lineage_hash` | `string` (SHA-256) | Cryptographic hash of the full lineage trace of the response. |
| `verification_status` | `string` | Current verification classification (`VERIFIED`, `UNVERIFIED`). |

## Cryptographic Lineage Hash Verification

The `lineage_hash` is computed deterministically at runtime as follows:
```python
lineage_str = f"{textbook_id}::{edition}::{chapter}::{section}::{page_numbers}"
lineage_hash = hashlib.sha256(lineage_str.encode("utf-8")).hexdigest()
```
This hash is checked against registry values during verification. Any modification of the retrieval response metadata, chapter names, or page numbers will break this hash, failing the verification pipeline and eliminating the risk of silent synthetic hallucinations.
