# Balbharati Official Catalog Datasets

These files were collected directly from `https://books.ebalbharati.in/` using
the deterministic collector in [scripts/collect_balbharati_catalog.py](/C:/Users/Yass0/OneDrive/Desktop/uniguru_3/uniguru_v2-main/scripts/collect_balbharati_catalog.py).

What is here:

- `collection_summary.json`: cross-year inventory and dataset hashes
- `site_taxonomy.json`: official site filter groups and option labels
- `year_<YEAR>_catalog.json`: per-year book catalog with official book ids,
  titles, cover URLs, and PDF URLs
- `year_2026_filter_membership.json`: book-to-filter mappings collected from
  the site for the live `2026` catalog
- `year_2026_catalog_enriched.json`: the `2026` catalog merged with its site
  filter membership

What is not here:

- No textbook PDFs were bulk-downloaded into the repo
- No OCR, chapter extraction, concept extraction, or exercise extraction was
  claimed by this collection step

Important note:

- The official site assigns multiple medium labels to some `2026` books. The
  collector preserves the site behavior exactly instead of collapsing it into a
  single inferred medium.
