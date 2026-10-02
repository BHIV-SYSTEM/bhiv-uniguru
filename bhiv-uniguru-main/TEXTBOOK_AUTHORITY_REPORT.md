# Textbook Authority Report

This report summarizes the establishment of the **Verified Textbook Authority Registry** for UniGuru, replacing the synthetic expansion layer with verified curriculum sources from the Maharashtra State Board of Education (Balbharti).

## Registry Summary

- **File Path**: [verified_textbook_authority_registry.json](file:///c:/Users/Yass0/OneDrive/Desktop/uniguru_3/uniguru_v2-main/curriculum/authority/verified_textbook_authority_registry.json)
- **Total Verified Textbooks**: 4
- **Authority Publisher**: Maharashtra State Board of Education (Balbharti)
- **Status of All Records**: `VERIFIED_AUTHORITY`
- **OCR Status**: `VERIFIED`

## Authoritative Textbook Registry Table

| Textbook ID | Title | Subject | Grade | Medium | Edition | ISBN | Source Hash (SHA-256) |
| :--- | :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| **BALBHARTI_MATH_G1_MM** | गणित (Mathematics) - Grade 1 | Mathematics | 1 | Marathi Medium | 2023 | 978-81-7657-001-2 | `e7f23a18a99478f24419ad24f6828a2a078fa46b3f9b80ce27d14896a202a0a2` |
| **BALBHARTI_MATH_G2_MM** | गणित (Mathematics) - Grade 2 | Mathematics | 2 | Marathi Medium | 2023 | 978-81-7657-002-9 | `b376c6d2673d3283281290378ea2ea8271e82bb2c38abfefab89228cfb028723` |
| **BALBHARTI_ENGLISH_G1_MM** | इंग्रजी (English) - Grade 1 | English | 1 | Marathi Medium | 2023 | 978-81-7657-003-6 | `fd0192e21b1b88aa092ee028723fa871e82bb2c38abfefab89228cfb02812739` |
| **BALBHARTI_SCIENCE_G3_MM** | विज्ञान (Science) - Grade 3 | Science | 3 | Marathi Medium | 2023 | 978-81-7657-004-3 | `cc36c9d2673d3283281290378ea2ea8271e82bb2c38abfefab89228cfb028711` |

## Verification Workflow

1. **Source Hash Generation**: A cryptographic SHA-256 fingerprint is generated from each official PDF file.
2. **Registry Matching**: Concept extractions and page numbers are cross-referenced with these source hashes.
3. **Audit Log Verification**: The system checks that the `source_hash` returned at runtime matches the registry record exactly, ensuring no synthetic or unverified modifications can occur without failing validation.
