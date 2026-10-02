# Dataset Migration and Isolation Report

## Migration Summary
This report outlines the migration and complete separation of synthetic curriculum records from canonical textbook evidence records.

- **Migration Timestamp**: 2026-06-20T18:07:40.004364+00:00
- **Isolate Status**: `COMPLETE`
- **Zero Synthetic in Canonical Path**: `ENFORCED`

### Statistics
| Metric | Before Migration | After Migration (Canonical) | After Migration (Experimental) |
| --- | --- | --- | --- |
| **Total Records** | 2560 | 42 | 2560 |
| **Synthetic Records** | 2560 | 0 | 2560 |
| **Verified Records** | 0 | 42 | 0 |
| **Synthetic Ratio** | 100.0% | 0.0% | 100.0% |

### Dataset File Mappings
- **Canonical Dataset**: `masterdb/balbharti/canonical_dataset.json` (Used by runtime)
- **Experimental Dataset**: `masterdb/balbharti/experimental_dataset.json` (Isolated)
- **Sample Dataset**: `masterdb/balbharti/sample_dataset.json` (Isolated)
- **Testing Dataset**: `masterdb/balbharti/testing_dataset.json` (Isolated)
