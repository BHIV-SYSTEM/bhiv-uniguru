# Core File Review

## backend/service/ecosystem_runtime.py
- Adds a deterministic ecosystem orchestration path that composes Vijay validation, TANTRA contract generation, Bucket telemetry, InsightFlow observability, GC validation, and MDU evidence generation.
- Emits proof artifacts to review_packets/integration_proof.
- Adds deterministic replay verification for stable cross-service fields without comparing timestamped transport metadata.

## backend/service/uniguru_runtime_api.py
- Exposes the new /runtime/ecosystem/execute endpoint without altering the existing runtime contract path.
- Exposes /runtime/ecosystem/replay for Vijay replay acceptance and /mitra/ecosystem/ask as the redacted governed Mitra interface.

## scripts/run_ecosystem_acceptance.py
- Drives live FastAPI request handling for health, readiness, metrics, ecosystem execution, replay and Mitra-facing acceptance.
- Regenerates review packet evidence under integration_proof, validation_reports, logs, deployment_proof and screenshots evidence folders.

## backend/kosha/kosha_retriever.py
- Includes a resilient fallback when the optional ontology-aware retriever dependency is absent so the deterministic pipeline remains testable.
