# MASTERDB Understanding

## Purpose
This document explains the MasterDB structure used by the UniGuru educational curriculum runtime.

## Canonical MasterDB Path

- `masterdb/` is the canonical ingestion directory for curriculum sources.
- `masterdb/balbharti/` contains the Balbharti starter MasterDB dataset and metadata.

## Key Files

- `masterdb/balbharti/sample_ingestion_dataset.json`
  - current sample seed containing 6 records for grades 1, 3, and 6 in both Marathi and English Medium.
- `masterdb/balbharti/balbharti_schema.json`
  - existing intake schema for Balbharti curriculum records.
- `masterdb/balbharti/ingestion_manifest.json`
  - generated manifest of dataset validity and coverage.
- `masterdb/masterdb_dashboard.json`
  - dashboard summary with subjects, grades, chapters, and missing curriculum coverage.

## Current Coverage

The sample seed covers:

- Subjects: Mathematics, EVS, Science
- Grades: 1, 3, 6
- Mediums: English Medium, Marathi Medium
- Chapters: Numbers, Water, Food, Sankhya, Pani, Anna

## Ingestion and Validation

- `scripts/ingest_balbharti_masterdb.py` validates records against required fields and generates the manifest proof artifact.
- Record validity is checked for required fields, supported grade ranges, supported media, and governance flags.
- The ingestion manifest includes:
  - `dataset_hash`
  - `manifest_hash`
  - `valid_record_count`
  - `mediums`, `grades`, `subjects`
  - `priority_band_coverage`

## What Remains to be Ingested

- Grades 2, 4, 5, 7, 8, 9, 10
- Subjects: History, Geography, Language
- Remaining chapters across all Balbharti standards and media
- Full curriculum versioning beyond the starter seed

## Operational Role

MasterDB is the authoritative educational knowledge source for curriculum-grounded answers in this sprint. The runtime matches student questions to MasterDB records and emits bounded, traceable responses.
