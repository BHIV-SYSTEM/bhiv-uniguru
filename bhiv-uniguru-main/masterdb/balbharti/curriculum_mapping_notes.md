# Balbharti Curriculum Mapping Notes

## Scope

This starter set establishes the governed structure for Balbharti MasterDB ingestion. It covers Marathi Medium and English Medium samples across the primary band and one secondary-band sample. It is not a complete curriculum import.

## Canonical Fields

Each curriculum unit must preserve:

- grade
- medium
- subject
- chapter
- concept
- definition
- examples
- questions
- language_variant
- source_lineage
- curriculum_version

## Priority Bands

Primary ingestion priority:

- Class 1-5
- Mathematics, EVS, Marathi, English

Secondary ingestion priority:

- Class 6-10
- Mathematics, Science, Social Science, History, Civics, Geography, Marathi, English

## Governance Rules

- PDFs are source inputs only; they are not the MasterDB object.
- Every extracted concept must become a structured record with source lineage.
- Sample seeds keep `canonical_authority_granted: false` until verified against source material.
- Marathi and English variants may map to the same concept family, but they must preserve language-specific wording and lineage.
- Contradictions across editions, media, or translations must be retained as review states instead of silently merged.

## Replay Discipline

The ingestion script emits a deterministic manifest hash over normalized records. That hash is used by the runtime as the retrieval and knowledge substrate boundary for replay-safe curriculum cognition.
