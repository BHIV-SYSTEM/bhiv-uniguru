# STT Integration Report

## Scope

UniGuru now exposes a deterministic voice ingress path:

`Microphone -> local STT engine -> language adapter -> conversation router -> UniGuru reasoning service`

The router remains the only reasoning gateway. No reasoning or ontology logic was modified.

## What Was Added

- `uniguru/stt/stt_engine.py`
  - Local STT boundary with provider abstraction.
  - `transformers` provider for a locally mounted ASR snapshot.
  - Deterministic `manifest` provider for CI and controlled test runs.
- `POST /voice/query` in `uniguru/service/api.py`
  - Accepts raw audio bytes.
  - Reads voice metadata from headers.
  - Runs STT, then feeds the transcript into the existing router path.
- Frontend microphone path in `Complete-Uniguru/frontend/src/components/EnhancedChatInput.tsx`
  - Replaced browser speech recognition with recorded audio upload to `/voice/query`.
  - Added Indian language selection for `en`, `hi`, `mr`, `ta`, `te`, `kn`, `bn`.

## Model Selection

Primary production target: AI4Bharat Indic ASR family mounted locally and loaded through the `transformers` provider.

Reason:

- strong Indian-language alignment
- local inference fits the sovereignty requirement
- backend-owned transcription keeps routing deterministic

Current repository default: `manifest` provider.

Reason:

- no model weights are vendored in this repo
- no ASR runtime packages are currently installed in the environment
- tests still need a deterministic offline path

## Runtime Contract

### Voice request

`POST /voice/query`

Body:

- raw audio bytes

Headers:

- `Content-Type`: audio mime type
- `X-Caller-Name`: caller identity
- `X-Audio-Filename`: original filename
- `X-Voice-Language`: optional language hint such as `hi`
- `X-Session-Id`: optional session identifier
- `X-Allow-Web`: optional `true|false`

### Response

Returns the normal router/reasoning payload plus:

```json
{
  "transcription": {
    "text": "...",
    "language": "hi",
    "confidence": 0.91,
    "provider": "manifest"
  }
}
```

## Configuration

### Default deterministic mode

```env
UNIGURU_STT_PROVIDER=manifest
UNIGURU_STT_MANIFEST_PATH=uniguru/stt/sample_manifest.json
```

### Production local-model mode

```env
UNIGURU_STT_PROVIDER=transformers
UNIGURU_STT_MODEL_PATH=/absolute/path/to/local/ai4bharat-asr-snapshot
```

## Validation

Executed:

- `pytest tests/test_stt_engine.py`
- `pytest tests/test_stt_integration_full.py`
- `python tests/test_stt_performance.py`

Result:

- `STT Engine Unit Tests: PASSED`
- `Multilingual Integration Tests: PASSED (hi, en, mr, ta, te, kn, bn)`
- `Performance Tests: PASSED (10 consecutive, 5 concurrent)`

Covered cases:

- voice query enters through STT and reaches router
- STT unavailability returns safe fallback payload
- manifest STT provider resolves deterministic local entries for multiple Indian languages
- concurrent voice queries handled without deadlocks

## Performance Results (Manifest Mode)

| Test Scenario | Result |
| --- | --- |
| 10 Consecutive Queries | Avg Latency: ~25ms |
| 5 Concurrent Queries | Success Rate: 100% |
| Multilingual Accuracy | 100% (Deterministic Manifest) |

## Current Limits

- This repo does not ship AI4Bharat model weights.
- This environment does not currently include `torch` / `transformers`.
- Frontend build verification could not be completed here because the local Node toolchain is incomplete (`tsc` unavailable in the current shell path).

## Primary Research Sources

- AI4Bharat: https://ai4bharat.org/
- BharatGen: https://bharatgen.org/
- AI Kosha: https://aikosha.gov.in/
