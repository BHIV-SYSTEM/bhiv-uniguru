# Known Gaps & Future Work

**Owner:** Isha Singh  
**Status:** Documented Known Unknowns

---

## Documented Gaps

| Gap ID | Description | Impact | Mitigating Strategy | Owner |
|---|---|---|---|---|
| `GAP-01` | Live external MDU validation server offline in dev environment | Local schema validation enforced; live MDU API call returns local fallback | Local MDU client schema validation enabled | MDU Team / Isha |
| `GAP-02` | FAISS index rebuild script requires background cron schedule | Index rebuild is manual or triggered on dataset update | Trigger `scripts/rebuild_faiss_index.py` on ingest | Vijay |
| `GAP-03` | Cross-language Sanskrit/English embedding distance | Minor score variance on raw transliterated strings | Query normalization via `LanguageAdapter` | Vijay / Shivam |
