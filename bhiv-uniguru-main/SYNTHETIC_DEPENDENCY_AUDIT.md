# Synthetic Content Dependency Audit

This audit was executed to scan the UniGuru repository and database for synthetic, placeholder, or generated content. Any found synthetic dependencies are detailed below to ensure full transparency and plan for curriculum authority hardening.

## Audit Summary

- **Audit Status**: `FLAGGED` (Synthetic content present in MasterDB)
- **Total Files Audited**: 8
- **Total Records Scanned**: 7839
- **Total Synthetic Elements Detected**: 2560
- **Synthetic Ratio**: 32.66%

---

## Detailed Findings By File

### File: `masterdb/balbharti/sample_ingestion_dataset.json`

- **Total Elements Scanned**: 7680
- **Synthetic Elements Detected**: 2560

#### Example Flaged Records:
- **ID**: `balbharti_en_g1_mathematics_numbers_1_01`
  - Reason: provenance_status: 'sample_seed'
  - Reason: source_type: 'curriculum_sample_seed'
  - Reason: ingestion_method: 'synthetic_expansion_seed'
  - Reason: generic concept name: 'Numbers concept 1'
- **ID**: `balbharti_en_g1_mathematics_numbers_1_02`
  - Reason: provenance_status: 'sample_seed'
  - Reason: source_type: 'curriculum_sample_seed'
  - Reason: ingestion_method: 'synthetic_expansion_seed'
  - Reason: generic concept name: 'Numbers concept 2'
- **ID**: `balbharti_en_g1_mathematics_shapes_2_01`
  - Reason: provenance_status: 'sample_seed'
  - Reason: source_type: 'curriculum_sample_seed'
  - Reason: ingestion_method: 'synthetic_expansion_seed'
  - Reason: generic concept name: 'Shapes concept 1'
- **ID**: `balbharti_en_g1_mathematics_shapes_2_02`
  - Reason: provenance_status: 'sample_seed'
  - Reason: source_type: 'curriculum_sample_seed'
  - Reason: ingestion_method: 'synthetic_expansion_seed'
  - Reason: generic concept name: 'Shapes concept 2'
- **ID**: `balbharti_en_g1_mathematics_patterns_3_01`
  - Reason: provenance_status: 'sample_seed'
  - Reason: source_type: 'curriculum_sample_seed'
  - Reason: ingestion_method: 'synthetic_expansion_seed'
  - Reason: generic concept name: 'Patterns concept 1'

---


## Remediation Plan

1. **Deprecated MasterDB Seeds**: The `sample_ingestion_dataset.json` currently contains mock expansion seeds. These records are flagged for deprecation in the production build.
2. **Hardened Verification**: All runtime flows must enforce a `verification_status` of `VERIFIED` and check that the textbook ID exists in the verified authority registry. Any unverified or synthetic matches must be flagged with `PARTIAL_VERIFIED_SAMPLE` or rejected.
