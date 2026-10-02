# Canonical Repo Map v2

## Purpose
This document captures the converged UniGuru repository structure for the educational runtime sprint. It makes explicit the single active runtime path, the canonical retrieval path, and the canonical MasterDB ingestion path.

## Canonical Top-Level Modules

- `/masterdb/` — canonical curriculum ingestion and dashboard structure
- `/retrieval/` — canonical MasterDB retrieval runtime interface
- `/curriculum/` — canonical curriculum schema and coverage reporting
- `/learning_runtime/` — canonical student-facing learning runtime flow
- `/review_packets/` — canonical package for convergence proof artifacts, handover, and understanding docs

## Surviving Modules

- `backend/service/uniguru_runtime_api.py` — canonical runtime execution surface for query -> MasterDB lookup -> constitutional runtime contract
- `backend/governance/constitutional_runtime.py` — canonical governance coordinator; not redesigned or duplicated
- `backend/retrieval/retriever.py` — supporting retrieval engine; remains available for legacy internal knowledge lookup
- `masterdb/balbharti/` — canonical Balbharti MasterDB ingestion seed, schema, and manifest
- `scripts/ingest_balbharti_masterdb.py` — canonical ingestion validation and manifest generation
- `review_packets/` — canonical delivery packaging for proof, understanding, and handover

## Retired or Secondary Paths

These paths are now treated as legacy or non-canonical regression surfaces in this sprint:

- `backend/service/api.py` — product API remains available but is not the primary runtime convergence path
- `backend/retrieval/web_retriever.py` — web retrieval branch remains secondary to MasterDB curriculum retrieval
- `backend/knowledge/` — supportive knowledge corpus directories remain available but are outside the curriculum-grounded MasterDB runtime path
- `docs/` and older `review_packets/` reports from prior governance-only sprints are preserved for reference, not active convergence execution

## Single Runtime Path

Canonical runtime path:

1. User query enters `retrieval/masterdb_retriever.py` or `backend/service/uniguru_runtime_api.py`
2. MasterDB lookup executes against `masterdb/balbharti/sample_ingestion_dataset.json`
3. Semantic interpretation produces a curriculum-aligned answer
4. `backend/governance/constitutional_runtime.py` governs trust, contradiction, and ontology boundaries
5. Payload is emitted as a bounded response contract and proof artifact

## Single Retrieval Path

Canonical retrieval path:

- `retrieval/masterdb_retriever.py` is the root retrieval adapter for curriculum queries
- it delegates to the canonical runtime entry point at `backend/service/uniguru_runtime_api.py`
- artifact output is produced as `retrieval/retrieval_artifact.json` or programmatically via `generate_retrieval_artifact(...)`

## Single MASTERDB Path

Canonical MasterDB path:

- `masterdb/balbharti/` contains the canonical Balbharti ingestion dataset, schema, manifest, and proof artifacts
- `masterdb/masterdb_dashboard.json` provides coverage visibility
- this path is the approved curriculum ingestion surface for the sprint

## Proof & Audit Artefacts

- `curriculum/curriculum_schema_v1.json`
- `curriculum/coverage_report.json`
- `masterdb/masterdb_dashboard.json`
- `learning_runtime/learning_runtime_flow.json`
- `review_packets/proof_logs/uniguru_runtime_execution_latest.json`
- `review_packets/proof_logs/balbharti_masterdb_ingestion_proof.json`

## Notes

This v2 canonical map does not redesign governance, does not create new authority systems, and does not create parallel runtimes. It consolidates the runtime into a single converged path while surface-level legacy support remains available for regression and reference.
