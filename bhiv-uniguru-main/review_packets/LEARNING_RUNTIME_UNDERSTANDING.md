# Learning Runtime Understanding

## Purpose
This document describes the student-facing learning runtime flow implemented in the sprint.

## Canonical Runtime Components

- `learning_runtime/runtime.py` — root pipeline for student question processing
- `learning_runtime/learning_runtime_flow.json` — documented flow and five subject examples
- `retrieval/masterdb_retriever.py` — canonical retrieval adapter for MasterDB curriculum lookup
- `backend/service/uniguru_runtime_api.py` — runtime execution surface for governance and trace emission

## Runtime Flow

The learning runtime follows these stages:

1. Student Question
2. Retrieval
3. Concept Match
4. Curriculum Mapping
5. Explanation
6. Follow-up Concepts
7. Learning Outcome
8. Trace Artifact

## How It Works

- A student question is routed through `retrieval/masterdb_retriever.py`.
- The query is matched against `masterdb/balbharti/sample_ingestion_dataset.json`.
- The runtime selects the best curriculum record based on query tokens, grade, medium, and subject.
- The matched record is interpreted into an answer, practice prompt, and learning outcome.
- Governance is applied via `backend/governance/constitutional_runtime.py` to produce trust, uncertainty, contradiction, and ontology metadata.
- The final payload includes a `trace_id`, `runtime_hash`, and `schema_version`.

## Example Output

A real example in the current seed:

- Question: "What is a balanced diet in Class 6 Science?"
- Matched concept: "Balanced diet"
- Curriculum version: `starter-2026-05`
- Learning outcome: "Understand the components of a balanced diet and identify examples of healthy meals."
- Trace artifact includes `trace_id`, `runtime_hash`, and output contract metadata.

## Student-Facing Design

The runtime is intentionally curriculum-aware rather than generative-only. It produces:

- a grounded explanation drawn directly from MasterDB records,
- concept-specific follow-up guidance,
- a mapped learning outcome,
- a trace artifact for transparency and proof.

## Next Integration Points

- Hook the learning runtime flow into the frontend student experience.
- Expand the curriculum dataset to support the full Balbharti subject and grade matrix.
- Add explicit follow-up outcomes for every matched record in the MasterDB seed.
