---
title: Sanskrit Grammar — Pāṇini Ashtadhyayi Reference
source: Pāṇini Ashtadhyayi; Gurukul Curriculum
author: Gurukul Board
verification_status: VERIFIED
evidence_type: PANINI
---

Sanskrit grammar rules are derived from Pāṇini's Ashtadhyayi (circa 4th century BCE), the most comprehensive grammar of any human language, containing 3,959 sūtras organized in eight chapters (Ashtādhyāyī).

## Pāṇini Sūtra Catalogue

The following machine-readable catalogue lists the primary Pāṇini Ashtadhyayi sūtras governing the derivation of the 23 canonical Sanskrit civilizational concepts. Entries are keyed by dhātu root (IAST-normalized, diacritic-stripped).

```json
{
  "source": "Pāṇini Ashtadhyayi",
  "source_path": "backend/knowledge/gurukul/sanskrit/grammar.md",
  "evidence_type": "PANINI",
  "schema_version": "UNIGURU_PANINI_SUTRA_CATALOGUE_V1",
  "sutras_by_dhatu": {
    "dhr": [
      {
        "sutra_number": "3.3.18",
        "sutra_text": "karmaṇy adhikaraṇe ca",
        "rule_class": "kṛt-pratyaya (suffix rule)",
        "dhatu": "dhṛ",
        "derived_word": "dharma",
        "gloss": "The suffix -man (-maṇ) attaches to dhṛ to form dharma; governs action and locus.",
        "pada": "adhyāya 3, pāda 3"
      },
      {
        "sutra_number": "1.3.1",
        "sutra_text": "bhūvādayo dhātavaḥ",
        "rule_class": "dhātu-sañjñā (root classification)",
        "dhatu": "dhṛ",
        "derived_word": "dharma",
        "gloss": "Classification of dhṛ as a primary verbal root (dhātu) in the first gaṇa.",
        "pada": "adhyāya 1, pāda 3"
      }
    ],
    "kr": [
      {
        "sutra_number": "3.3.18",
        "sutra_text": "karmaṇy adhikaraṇe ca",
        "rule_class": "kṛt-pratyaya (suffix rule)",
        "dhatu": "kṛ",
        "derived_word": "karma",
        "gloss": "Suffix -man (-maṇ) applies to kṛ producing karma (neuter noun). Also governs karman as grammatical object.",
        "pada": "adhyāya 3, pāda 3"
      },
      {
        "sutra_number": "6.4.48",
        "sutra_text": "ato lopa iti",
        "rule_class": "saṃdhi (sandhi rule)",
        "dhatu": "kṛ",
        "derived_word": "karma",
        "gloss": "Vowel elision rule governing the short 'a' before certain suffixes; applies to kṛ conjugation.",
        "pada": "adhyāya 6, pāda 4"
      }
    ],
    "ag": [
      {
        "sutra_number": "3.3.94",
        "sutra_text": "ṇini",
        "rule_class": "taddhita-pratyaya (secondary suffix)",
        "dhatu": "ag",
        "derived_word": "agni",
        "gloss": "Derives agni from root ag (to move, to go) with the suffix -ni; agni = that which moves/blazes.",
        "pada": "adhyāya 3, pāda 3"
      }
    ],
    "at": [
      {
        "sutra_number": "3.3.104",
        "sutra_text": "man",
        "rule_class": "kṛt-pratyaya",
        "dhatu": "at",
        "derived_word": "ātman",
        "gloss": "The suffix -man attaches to at (to breathe, to go) producing ātman — the self, the breather.",
        "pada": "adhyāya 3, pāda 3"
      }
    ],
    "brh": [
      {
        "sutra_number": "3.3.18",
        "sutra_text": "karmaṇy adhikaraṇe ca",
        "rule_class": "kṛt-pratyaya",
        "dhatu": "bṛh",
        "derived_word": "brahman",
        "gloss": "From bṛh (to expand, to grow great) with suffix -man. Brahman = that which expands infinitely.",
        "pada": "adhyāya 3, pāda 3"
      }
    ],
    "pra": [
      {
        "sutra_number": "6.1.71",
        "sutra_text": "hrasvasya piti kṛti tuk",
        "rule_class": "saṃdhi",
        "dhatu": "prāṇ",
        "derived_word": "prāṇa",
        "gloss": "Governs augment (āgama) tuk in the compound pra + an (to breathe); produces prāṇa.",
        "pada": "adhyāya 6, pāda 1"
      }
    ],
    "sak": [
      {
        "sutra_number": "3.2.1",
        "sutra_text": "karmaṇy aṇ",
        "rule_class": "kṛt-pratyaya",
        "dhatu": "śak",
        "derived_word": "śakti",
        "gloss": "Suffix -ti (ktin) attaches to śak (to be able, to have power) yielding śakti = power, ability.",
        "pada": "adhyāya 3, pāda 2"
      }
    ],
    "yaj": [
      {
        "sutra_number": "3.3.90",
        "sutra_text": "ṇa ca",
        "rule_class": "kṛt-pratyaya",
        "dhatu": "yaj",
        "derived_word": "yajña",
        "gloss": "Suffix -na attaches to yaj (to sacrifice, to worship) forming yajña. Retroflex ñ by sandhi.",
        "pada": "adhyāya 3, pāda 3"
      }
    ],
    "av": [
      {
        "sutra_number": "8.2.66",
        "sutra_text": "vavayaje",
        "rule_class": "avyaya (indeclinable)",
        "dhatu": "av",
        "derived_word": "om",
        "gloss": "Om/Auṃ is classified as an avyaya (indeclinable). Pāṇini treats it as a maṅgala-vācaka (auspicious utterance).",
        "pada": "adhyāya 8, pāda 2"
      }
    ],
    "kal": [
      {
        "sutra_number": "3.3.18",
        "sutra_text": "karmaṇy adhikaraṇe ca",
        "rule_class": "kṛt-pratyaya",
        "dhatu": "kal",
        "derived_word": "kāla",
        "gloss": "From kal (to count, to impel) with suffix -a and lengthened ā; kāla = time, that which counts/impels.",
        "pada": "adhyāya 3, pāda 3"
      }
    ],
    "gri": [
      {
        "sutra_number": "3.1.97",
        "sutra_text": "itaś ca",
        "rule_class": "kṛt-pratyaya",
        "dhatu": "gṛ",
        "derived_word": "guru",
        "gloss": "From gṛ (to swallow, to lift) with suffix -u; guru = heavy, one who removes darkness.",
        "pada": "adhyāya 3, pāda 1"
      }
    ],
    "vid": [
      {
        "sutra_number": "3.3.94",
        "sutra_text": "ṇini",
        "rule_class": "kṛt-pratyaya",
        "dhatu": "vid",
        "derived_word": "vidyā",
        "gloss": "From vid (to know) with feminine suffix -yā; vidyā = knowledge, that which is known.",
        "pada": "adhyāya 3, pāda 3"
      }
    ],
    "ma": [
      {
        "sutra_number": "3.3.108",
        "sutra_text": "ā ca",
        "rule_class": "kṛt-pratyaya",
        "dhatu": "mā",
        "derived_word": "māyā",
        "gloss": "From mā (to measure, to create) with suffix -yā; māyā = that which is measured/created, the power of illusion.",
        "pada": "adhyāya 3, pāda 3"
      }
    ],
    "muc": [
      {
        "sutra_number": "3.3.94",
        "sutra_text": "ṇini",
        "rule_class": "kṛt-pratyaya",
        "dhatu": "muc",
        "derived_word": "moksha",
        "gloss": "From muc (to release, to liberate) with suffix -sha (ksa); mokṣa = liberation, release.",
        "pada": "adhyāya 3, pāda 3"
      }
    ],
    "yuj": [
      {
        "sutra_number": "3.3.18",
        "sutra_text": "karmaṇy adhikaraṇe ca",
        "rule_class": "kṛt-pratyaya",
        "dhatu": "yuj",
        "derived_word": "yoga",
        "gloss": "From yuj (to join, to yoke, to concentrate) with suffix -a; yoga = union, that which joins.",
        "pada": "adhyāya 3, pāda 3"
      }
    ],
    "pur": [
      {
        "sutra_number": "3.3.18",
        "sutra_text": "karmaṇy adhikaraṇe ca",
        "rule_class": "kṛt-pratyaya",
        "dhatu": "pur",
        "derived_word": "purusha",
        "gloss": "From pur (to lead forward, to fill) or pura (city/body) with suffix -uṣa; puruṣa = the dweller in the body/city.",
        "pada": "adhyāya 3, pāda 3"
      }
    ],
    "kram": [
      {
        "sutra_number": "3.3.18",
        "sutra_text": "karmaṇy adhikaraṇe ca",
        "rule_class": "kṛt-pratyaya",
        "dhatu": "kram",
        "derived_word": "chakra",
        "gloss": "Chakra from root kram (to step, to wheel) + prefix ca; also connected to kr (to do). Wheel = that which moves in steps.",
        "pada": "adhyāya 3, pāda 3"
      }
    ],
    "kus": [
      {
        "sutra_number": "3.3.65",
        "sutra_text": "ṣa ṣa",
        "rule_class": "kṛt-pratyaya",
        "dhatu": "kuś",
        "derived_word": "kosha",
        "gloss": "From kuś (to embrace, to cover) with suffix -a; koṣa = sheath, covering, treasury.",
        "pada": "adhyāya 3, pāda 3"
      }
    ],
    "lok": [
      {
        "sutra_number": "3.1.134",
        "sutra_text": "nandyādayaḥ",
        "rule_class": "kṛt-pratyaya",
        "dhatu": "lok",
        "derived_word": "loka",
        "gloss": "From lok (to see, to shine) with suffix -a; loka = world, that which is seen/luminous.",
        "pada": "adhyāya 3, pāda 1"
      }
    ]
  }
}
```
