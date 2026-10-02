# Runtime Dataset Validation

## Isolation Architecture
The UniGuru production runtime has been modified to ensure that all retrieval calls load records exclusively from the canonical dataset.

### Verification Rules
1. **Access Path Restrictions**: The `retrieval_engine.py` points directly to `canonical_dataset.json`. The older `sample_ingestion_dataset.json` has been deprecated and its file access references removed.
2. **Provenance Status Auditing**: Every retrieved record is validated to ensure its `provenance_status` is `VERIFIED` and `canonical_authority_granted` is `True`.
3. **Safety Gates**: If any record with `provenance_status == "sample_seed"` or containing synthetic metadata is retrieved in the canonical path, the safety gate immediately aborts execution.
