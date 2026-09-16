# Licensed Balbharti Textbook Drop

Licensed textbook binaries are confidential BHIV ecosystem assets and must not be committed.
Place acquired files under the deterministic hierarchy below before running production ingestion:

```text
masterdb/balbharti/licensed_textbooks/
  <publisher>/
    <board>/
      <medium>/
        class_<class>/
          <subject>/
            edition_<edition>/
              source.pdf
              source.sha256
              acquisition_receipt.json
              samachar_extraction.json
              validation_evidence.json
```

Production gates require publisher authority, source hash, page evidence, lineage hash,
retrieval hash, OCR status, and independent Vijay/Codex cross-validation before merge.
