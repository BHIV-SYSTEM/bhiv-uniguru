# Failure Report

## What Still Breaks

- MasterDB contains a starter sample set only, not full Balbharti Class 1-10 coverage.
- Source verification is not complete; sample records intentionally keep `canonical_authority_granted: false`.
- Runtime retrieval is deterministic lexical matching, not a production vector or hybrid curriculum retriever.
- The FastAPI runtime endpoint is implemented but not wired into the existing `service.api` app router.
- File-backed proof logs are not a concurrent production event store.

## What Is Simulated

- Distributed arbitration nodes are named deterministic participants, not networked consensus.
- Replay trust is hash-chain proof, not signed distributed attestation.
- Curriculum source references are starter lineage labels, not verified page-level citations from official PDFs.
- SPLM token accounting is a readiness framework, not a live trainer.

## What Is Real

- A callable runtime exists at `backend/service/uniguru_runtime_api.py`.
- Runtime contract output contains the mandatory fields.
- MasterDB records are structured curriculum units with Marathi and English samples.
- Ingestion emits deterministic record, dataset, and manifest hashes.
- Runtime execution emits replay artifacts and bounded trust/ontology/contradiction states.

## What Remains Missing

- Full Balbharti ingestion for Class 1-10 across all target subjects.
- Official PDF/source acquisition and page-level extraction validation.
- Human curriculum review workflow.
- Production storage for MasterDB, replay events, and contradiction queues.
- Integration into frontend user flows.
- Signed replay batches and stronger distributed trust boundaries.

## Production Readiness Blockers

- Canonical curriculum authority cannot be granted until source verification is complete.
- Retrieval quality must move beyond sample lexical search.
- Runtime proof artifacts need durable storage and access controls.
- Contradiction and ontology alert queues need owner assignment and review deadlines.
- Existing backend API must route product traffic through the canonical runtime contract.
