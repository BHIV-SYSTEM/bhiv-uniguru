# REVIEW_PACKET.md — Isha Task: Kosha Enforcement + OCR Purification + Deterministic Answer Layer

**Generated:** 2026-05-05  
**Task:** Transition UniGuru from "working system" to trustworthy knowledge system  
**Handover to:** Vijay Dhawan + Soham

---

## Entry Point

**Primary endpoint:** `POST /new_rag` and `POST /new_query` in `backend/service/api.py`

**New deterministic pipeline entry point:**
```
backend/kosha/deterministic_pipeline.py → run_deterministic_pipeline(query)
```

**Proof log runner:**
```
backend/run_proof_log.py
```

---

## Core Flow (3 Files)

```
1. backend/kosha/ocr_purifier.py
   OCRPurifier.clean(text) → removes noise, broken Unicode, garbage lines
   OCRPurifier.measure_ocr_quality(text) → returns 0.0–1.0 quality score

2. backend/kosha/kosha_enforcer.py
   KoshaEnforcer.build_entry(content, source) → validated KoshaEntry or None
   KoshaEnforcer.validate_existing_entries(entries) → stats + valid list
   KoshaEnforcer.compute_confidence(...) → real score from 4 factors

3. backend/kosha/signal_validator.py
   SignalValidator.validate_all(signals, query) → accepted + rejected with reasons
   AnswerSynthesizer.synthesize(query, validation_result) → clean answer or NO_VERIFIED_KNOWLEDGE
```

**Supporting files (unchanged structure, updated behavior):**
- `backend/kosha/kosha_retriever.py` — now passes `tags` and `domain` in signals
- `backend/kosha/kosha_loader.py` — unchanged
- `backend/kosha/kosha_validator.py` — unchanged (schema source of truth)

---

## Real Input / Output

### Query with verified knowledge:
```
Input:  "Tell me about the Upanishads"
Output: {
  "answer": "The Upanishads expound the secret meaning of the Vedas and treat of Brahma...",
  "verification_status": "VERIFIED",
  "confidence": 0.5,
  "signals_found": 1,
  "signals_rejected": 0,
  "reasoning": "Signal matched via tags ['upanishads'] with content overlap 1.00. Confidence: 0.500."
}
```

### Query with NO verified knowledge:
```
Input:  "What is the current stock price of Apple?"
Output: {
  "answer": "I do not have verified knowledge to answer this question.",
  "verification_status": "NO_VERIFIED_KNOWLEDGE",
  "confidence": 0.0,
  "signals_found": 0,
  "signals_rejected": 0,
  "reasoning": "No signals passed domain+tag+query validation."
}
```

### Query with partial match (signals rejected):
```
Input:  "What does the Ramayana teach?"
Output: {
  "answer": "The texts that describe stories of gods and creation are the Valmiki-Ramayana...",
  "verification_status": "VERIFIED",
  "confidence": 0.333,
  "signals_found": 1,
  "signals_rejected": 1,
  "reasoning": "Signal matched via tags [] with content overlap 0.50. Confidence: 0.333."
}
```

---

## What Changed

### BEFORE (old system problems):
1. **Silent LLM fallback** — when Kosha had no match, system silently called Groq LLM and returned hallucinated answers with no indication it was LLM-generated
2. **No OCR purification** — raw OCR garbage (broken line breaks, noise chars, "I don't know" content) was stored as valid Kosha entries (e.g., `KOSHA_41c193e6f2b1.json` contains fragmented OCR text; `KOSHA_7095be79628d.json` has content = "I don't know.")
3. **Arbitrary confidence** — confidence values were FAISS cosine similarity scores, not based on content quality, OCR quality, or tag match
4. **No signal validation** — any signal with confidence > 0 was accepted, regardless of whether it matched the query domain or tags
5. **No explicit rejection** — system never returned "I do not have verified knowledge" — it always generated something

### AFTER (new deterministic system):
1. **Explicit NO_VERIFIED_KNOWLEDGE** — when no signal passes validation, returns exact string: `"I do not have verified knowledge to answer this question."` with `verification_status: "NO_VERIFIED_KNOWLEDGE"`
2. **OCR purification layer** (`ocr_purifier.py`) — removes noise patterns, broken Unicode, garbage lines, validates minimum quality before any entry is used
3. **Real confidence scoring** (`kosha_enforcer.py`) — 4-factor formula: content clarity (40%) + OCR quality (30%) + tag match (20%) + domain match (10%)
4. **Deterministic signal validation** (`signal_validator.py`) — every signal must pass: content exists + confidence ≥ 0.15 + (tag overlap OR content overlap > 10%)
5. **Explicit rejection logging** — every rejected signal has a named reason: `empty_or_short_content`, `confidence_below_threshold:X.XXX`, `no_query_relevance:tags_and_content_both_miss`

---

## Failure Cases

| Failure | Behavior |
|---------|----------|
| No Kosha entries loaded | Returns `NO_VERIFIED_KNOWLEDGE` with reason "No valid Kosha entries passed schema enforcement" |
| All signals below confidence threshold | Returns `NO_VERIFIED_KNOWLEDGE` with rejection reasons listed |
| Content is "I don't know" | `KoshaEnforcer._is_non_answer()` rejects entry at enforcement phase |
| OCR garbage text | `OCRPurifier.clean()` returns None, entry is not built |
| Query has no matching domain/tags | `SignalValidator` rejects all signals, returns `NO_VERIFIED_KNOWLEDGE` |
| Out-of-domain query (stock prices, news, etc.) | No signals match → `NO_VERIFIED_KNOWLEDGE` |

---

## Proof: 5 Queries Returning "I do not have verified knowledge"

From `review_packets/proof_log.json` (22 queries run, 12 returned NO_VERIFIED_KNOWLEDGE):

| # | Query | Justification |
|---|-------|---------------|
| 1 | "What is the current stock price of Apple?" | No Kosha entries contain financial market data |
| 2 | "Who won the cricket match yesterday?" | No Kosha entries contain sports/current events |
| 3 | "What is the latest news from Ukraine?" | No Kosha entries contain current news |
| 4 | "Explain quantum entanglement in physics" | No Kosha entries match physics domain with quantum entanglement content |
| 5 | "What is the GDP of India in 2024?" | No Kosha entries contain economic statistics |
| 6 | "How do I fix a Python import error?" | No Kosha entries contain programming content |
| 7 | "What is the recipe for biryani?" | No Kosha entries contain culinary content |

---

## Proof Log Location

Full 22-query proof log with signals found/rejected/confidence reasoning:
```
review_packets/proof_log.json
```

Run it yourself:
```bash
cd backend
python run_proof_log.py
```

---

## New Files Created

| File | Purpose |
|------|---------|
| `backend/kosha/ocr_purifier.py` | Phase 2: OCR noise removal + quality scoring |
| `backend/kosha/kosha_enforcer.py` | Phase 3+5: Schema enforcement + real confidence scoring |
| `backend/kosha/signal_validator.py` | Phase 4+6: Signal validation + answer synthesis |
| `backend/kosha/deterministic_pipeline.py` | Full pipeline orchestrator (no LLM) |
| `backend/run_proof_log.py` | 22-query proof log generator |

## Modified Files

| File | Change |
|------|--------|
| `backend/kosha/__init__.py` | Added exports for new modules |
| `backend/kosha/kosha_retriever.py` | Signals now include `tags` and `domain` fields |
