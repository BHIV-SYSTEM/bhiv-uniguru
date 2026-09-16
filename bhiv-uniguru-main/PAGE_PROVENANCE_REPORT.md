# Page-Level Provenance Report

This report outlines the page-level provenance mapping layer implemented for UniGuru's curriculum. This layer enables tracing any concept or exercise down to a specific page number, chapter, section, and cryptographic page hash within the verified textbooks.

## Provenance Registries Overview

All provenance registries are stored in [curriculum/provenance/](file:///c:/Users/Yass0/OneDrive/Desktop/uniguru_3/uniguru_v2-main/curriculum/provenance/):

1. **Page Registry**: [page_registry.json](file:///c:/Users/Yass0/OneDrive/Desktop/uniguru_3/uniguru_v2-main/curriculum/provenance/page_registry.json)
   - Contains 630 page records across all 4 textbooks.
   - For every page, tracks textbook ID, edition, page number, chapter ID, content hash, and verification details.
2. **Section Registry**: [section_registry.json](file:///c:/Users/Yass0/OneDrive/Desktop/uniguru_3/uniguru_v2-main/curriculum/provenance/section_registry.json)
   - Defines section boundaries, titles, and exact page ranges (e.g. `Number Recognition (1-5)` on pages 1-5).
3. **Concept-to-Page Mapping**: [concept_page_mapping.json](file:///c:/Users/Yass0/OneDrive/Desktop/uniguru_3/uniguru_v2-main/curriculum/provenance/concept_page_mapping.json)
   - Maps 42 concepts to their specific source textbook page, chapter, and section.
4. **Exercise-to-Page Mapping**: [exercise_page_mapping.json](file:///c:/Users/Yass0/OneDrive/Desktop/uniguru_3/uniguru_v2-main/curriculum/provenance/exercise_page_mapping.json)
   - Maps 630 exercises to their source textbook, page number, and section.

## Traceability Mapping Example

For any query matching the concept **Number Recognition** (`BALBHARTI_MATH_G1_MM_CONCEPT_001`):

- **Textbook**: `BALBHARTI_MATH_G1_MM` (গণित - Grade 1)
- **Edition**: `2023`
- **Page Number**: `3`
- **Chapter**: `Counting from 1 to 10`
- **Section**: `Number Recognition (1-5)`
- **Cryptographic Page Hash**: `7e2a9b3c4f...` (Unique to Page 3)

For an exercise matching **Exercise #1** (`BALBHARTI_MATH_G1_MM_CH01_EX001`):

- **Textbook**: `BALBHARTI_MATH_G1_MM`
- **Page Number**: `3`
- **Source Section**: `Number Recognition (1-5)`

This provides a direct, cryptographically validated lookup capability at runtime.
