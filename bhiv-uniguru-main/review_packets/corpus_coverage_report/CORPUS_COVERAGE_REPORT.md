# Corpus Coverage Report — Sanskrit Knowledge Decoder (Phases 1–6)

## Corpus Overview

The UniGuru Sanskrit Knowledge Corpus contains **23 canonical Sanskrit concept records** located under `backend/knowledge/sanskrit/`. Each concept record is fully structured into 35 standardized civilizational knowledge sections.

## Concept Matrix & Layer Coverage

| Concept | Canonical File | Total Layers | Evidence-Backed Layers | Coverage % | Node Count in Graph |
| --- | --- | --- | --- | --- | --- |
| **Dharma** | `dharma.md` | 35 | 31 | 88.6% | 28 |
| **Karma** | `karma.md` | 35 | 31 | 88.6% | 26 |
| **Agni** | `agni.md` | 35 | 31 | 88.6% | 20 |
| **Ātman** | `atman.md` | 35 | 31 | 88.6% | 21 |
| **Brahman** | `brahman.md` | 35 | 31 | 88.6% | 26 |
| **Prāṇa** | `prana.md` | 35 | 30 | 85.7% | 23 |
| **Ṛta** | `rta.md` | 35 | 30 | 85.7% | 13 |
| **Śakti** | `shakti.md` | 35 | 31 | 88.6% | 24 |
| **Yajña** | `yajna.md` | 35 | 31 | 88.6% | 19 |
| **Om** | `om.md` | 35 | 31 | 88.6% | 26 |
| **Kāla** | `kala.md` | 35 | 31 | 88.6% | 18 |
| **Ākāśa** | `akasha.md` | 35 | 31 | 88.6% | 16 |
| **Guru** | `guru.md` | 35 | 31 | 88.6% | 19 |
| **Vidyā** | `vidya.md` | 35 | 31 | 88.6% | 19 |
| **Saṃskāra** | `samskara.md` | 35 | 31 | 88.6% | 14 |
| **Māyā** | `maya.md` | 35 | 31 | 88.6% | 17 |
| **Prakṛti** | `prakrti.md` | 35 | 31 | 88.6% | 17 |
| **Puruṣa** | `purusha.md` | 35 | 31 | 88.6% | 18 |
| **Lokas** | `lokas.md` [NEW] | 35 | 32 | 91.4% | 36 |
| **Koshas** | `koshas.md` [NEW] | 35 | 32 | 91.4% | 32 |
| **Chakras** | `chakras.md` [NEW] | 35 | 32 | 91.4% | 36 |
| **Moksha** | `moksha.md` | 35 | 31 | 88.6% | 26 |
| **Yoga** | `yoga.md` | 35 | 31 | 88.6% | 28 |

## 35-Layer Schema Population

1. **Lexical & Vedāṅga Core**: `sanskrit`, `shabda` (with acoustic phonetics), `dhatu`, `vyakarana` (with Pāṇini Ashtadhyayi sūtras), `nirukta`, `beeja` (with Śikṣā phonetics), `tattva`, `shakti`, `literal_meaning`, `functional_meaning`
2. **Applied Disciplines**: `ontology`, `cosmology`, `psychology`, `governance`, `medicine`, `engineering`, `mathematics`, `astronomy`, `metallurgy`, `ritual`, `symbolism`
3. **Cross-Tradition Relations**: `related_deities`, `related_lokas`, `related_koshas`, `related_chakras`, `related_yantras`, `related_mantras`, `related_vidyas`, `related_shastras`
4. **Historical & Hermeneutic**: `traditional_interpretations`, `historical_evolution`, `cross_references`, `comparative_hermeneutics` (structured Darśana matrix)
5. **Research Frontiers**: `open_research_questions`, `experimental_hypotheses`

## Zero Generative Fallback Policy

- **100% Source-Scoped**: No ungrounded text generation is performed.
- **Explicit Classification**: Unmatched layers are marked `NO_RETRIEVED_EVIDENCE` or `NOT_ASSERTED`.
- **Explicit Experimental Marking**: Experimental hypotheses are tagged `EXPLICITLY_MARKED_EXPERIMENTAL` with policy boundary enforcement.
