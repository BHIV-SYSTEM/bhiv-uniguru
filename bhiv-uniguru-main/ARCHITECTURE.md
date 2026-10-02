# TANTRA Curriculum Intelligence Runtime - Architecture

## 1. Purpose

The TANTRA Curriculum Intelligence Runtime is a reusable deterministic capability consumed by UniGuru.

Its purpose is to provide evidence-first curriculum intelligence through the existing canonical runtime boundary without introducing a product-specific curriculum implementation.

Capability: tantra.curriculum_intelligence

Provider: TANTRA

Consumer: UniGuru

## 2. Architectural Principle

The runtime follows these principles:

- deterministic execution
- evidence-first retrieval
- canonical curriculum provenance
- explicit verification status
- replay-safe execution
- bounded failure behavior
- capability-first integration
- no silent downgrade from unsupported curriculum evidence to unverified curriculum answers

The runtime reuses the existing UniGuru runtime rather than creating a parallel execution architecture.

## 3. Capability Boundary

| Property | Value |
|---|---|
| Capability ID | tantra.curriculum_intelligence |
| Version | 1.0.0 |
| Schema | TANTRA_CURRICULUM_INTELLIGENCE_CAPABILITY_V1 |
| Provider | TANTRA |
| Domain | curriculum_intelligence |
| Execution mode | deterministic |
| Evidence required | true |
| Replay safe | true |
| Consumer | UniGuru |
| Canonical runtime | learning_runtime.canonical_runtime.execute_query |

## 4. Runtime Flow

The validated runtime boundary is:

Student Query
->
UniGuru Router
->
TANTRA Curriculum Intelligence
->
Canonical Retrieval
->
Evidence / Verification
->
Curriculum Intelligence
->
Learning Intelligence
->
Mastery Intelligence
->
Constitutional Runtime
->
Runtime Contract

Unsupported curriculum evidence terminates at the canonical safety gate before an unverified curriculum response can be produced.

## 5. Major Runtime Components

### Canonical Runtime

The canonical execution surface is:

learning_runtime.canonical_runtime.execute_query

### Retrieval

The retrieval layer resolves supported curriculum queries against canonical curriculum records and exposes retrieval status and confidence.

### Evidence / Provenance

Successful execution carries evidence identity and provenance information including:

- evidence ID
- textbook ID
- edition
- chapter
- section
- page numbers
- source hash
- retrieval hash
- lineage hash
- verification status

### Curriculum Intelligence

The capability resolves curriculum concepts and produces concept, chapter, subject, definition, learning outcome, source lineage, curriculum version and matched-record information.

### Learning Intelligence

The canonical runtime continues into learning intelligence and can produce learning outcome, learning gap information, learning path, next concept, practice recommendations and remediation information.

### Mastery Intelligence

The runtime includes mastery state and related learning-progress information as part of the canonical pipeline.

### Constitutional Runtime

Validated positive execution reaches the constitutional runtime with:

active = true
decision = forward
enforced = true

## 6. Evidence Model

A valid curriculum response requires canonical evidence.

Validated positive example:

- Textbook: BALBHARTI_MATH_G1_MM
- Edition: 2023
- Chapter: Counting from 1 to 10
- Section: Number Recognition (1-5)
- Page: 3
- Verification: VERIFIED

The runtime emits source, retrieval and lineage hashes.

## 7. Determinism

The capability metadata declares deterministic execution.

Validation includes capability metadata, canonical retrieval matching, retrieval confidence, evidence identifiers and automated runtime assertions.

The automated suite reports:

18 passed

## 8. Replay Safety

The capability metadata declares:

replay_safe = true

The runtime exposes request, evidence, retrieval and lineage information required for traceability within the validated runtime scope.

## 9. Failure / Safety Boundary

Unsupported curriculum evidence is refused.

Validated negative request:

Explain quantum teleportation using a fictional Balbharti chapter that does not exist

Observed result:

verification_status = BLOCKED
blocked = true
convergence_validated = false

Block reason:

[SAFETY_GATE] Evidence failure: no canonical retrieval match. Refusing execution.

The negative path does not produce canonical evidence or retrieval results.

## 10. Runtime Contract

The validated positive pipeline completes at RuntimeContract.

Pipeline stages:

- StudentQuery
- Retrieval
- CurriculumIntelligence
- LearningIntelligence
- MasteryIntelligence
- ConstitutionalRuntime
- RuntimeContract

The positive runtime reports:

convergence_validated = true

## 11. Observability

Runtime evidence is captured through timestamp, verification status, evidence ID, source hash, retrieval hash, lineage hash, retrieval metadata, pipeline trace, pipeline stages and total latency.

Runtime health validation covered:

- /health
- /ready
- /health/live

## 12. Deployment Architecture

The repository contains containerized deployment configuration using a Python application container, Node backend, Nginx, Certbot and Docker Compose.

Deployment artifacts are preserved in:

evidence_packet/deployment_proof/

Environment-specific production deployment remains subject to target-environment validation.

## 13. Current Limitations

The following remain outside the currently validated engineering scope:

- target production environment validation
- environment-specific configuration validation
- observer approval
- formal handover acceptance

These items must not be inferred from local runtime or CI validation.

## 14. Architectural Convergence

No duplicate TANTRA curriculum implementation is required.

The capability remains attached to the existing UniGuru runtime and canonical execution boundary.
