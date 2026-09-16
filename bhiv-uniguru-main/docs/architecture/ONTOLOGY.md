# ONTOLOGY SCHEMA FREEZE REPORT

## Status: IMMUTABLE

This document serves as the canonical definition for the **UniGuru Concept Schema**. This schema is now frozen. No dynamic fields or structural mutations are permitted without a formal version bump and drift analysis.

### 1. Concept Fields (Required)

| Field | Type | Description |
| :--- | :--- | :--- |
| `concept_id` | UUID | Immutable unique identifier. |
| `canonical_name` | String | Standardized name for the concept. |
| `parent_id` | UUID \| None | Link to parent concept for structural hierarchy. |
| `truth_level` | Integer | Assigned truth depth (0–4). |
| `domain` | Enum | Classification: `quantum`, `jain`, `swaminarayan`, `gurukul`, `core`. |
| `source_reference`| String | Direct URI or file path to knowledge origin. |
| `snapshot_version`| Integer | The snapshot version in which this concept was defined. |
| `created_at` | Timestamp | ISO 8601 formatting (UTC). |
| `immutable` | Boolean | Hard flag indicating structural stability. |

### 2. Strict Truth Levels

| Level | Name | Definition |
| :--- | :--- | :--- |
| **0** | Unknown | Unprocessed or conflicting data. |
| **1** | Partially Verified | Source exists but cross-referencing is pending. |
| **2** | Verified Secondary | Confirmed by secondary sources/commentaries. |
| **3** | Canonical Verified | Matches primary canonical source (Shastras/Text). |
| **4** | Foundational Immutable | Core ontological axioms (Root Nodes). |

### 3. Implementation Guardrails

- **Acyclic Enforcement**: The `OntologyGraph` enforces a Directed Acyclic Graph (DAG) structure; no concept can parent itself or form cycles.
- **Frozen Dataclass**: The `Concept` implementation in `uniguru/ontology/schema.py` uses `frozen=True` to prevent runtime mutation.
- **Schema Validation**: `validate_concept_dict` will reject any payload containing extra or missing fields.

### 4. Integrity Seal

The schema logic is contained in `uniguru/ontology/schema.py` and is currently protected by deterministic hashing in the snapshot system.


## Merged: GRAPH_VALIDATION_REPORT.md

# GRAPH_VALIDATION_REPORT

## Implemented Validation Rules
Code: `uniguru/ontology/graph.py`

1. Single Root Constraint
- Exactly one concept must have `parent_id = null`.
- Violations raise `ValueError("Single root constraint violated...")`.

2. Parent Existence Validation
- Every non-root node must point to an existing parent id.
- Missing parent raises `ValueError("Parent concept missing...")`.

3. Cycle Detection
- Deterministic DFS traversal over graph adjacency.
- Back-edge detection raises `ValueError("Ontology cycle detected...")`.

4. Domain Constraints
- Allowed domains only:
  - `quantum`
  - `jain`
  - `swaminarayan`
  - `gurukul`
  - `core`
- Any out-of-contract domain is rejected.

5. Deterministic Snapshot Gate
- `SnapshotManager.load_snapshot` now validates schema and constructs `OntologyGraph`.
- Invalid graph snapshots are rejected before runtime use.


## Merged: ONTOLOGY_HARDENING_REPORT.md

# ONTOLOGY_HARDENING_REPORT

## 1) Immutable Concept Enforcement
Implemented in `uniguru/ontology/drift_detector.py`.

If `immutable=true` in a prior snapshot, the following are now hard-rejected:
- parent change
- canonical name change
- truth downgrade
- domain reassignment

Rejected changes produce:
- `type: immutable_concept_violation`
- `accepted: false`
- `rejected: true`

## 2) Graph Validation Hardening
Implemented in `uniguru/ontology/graph.py` and enforced during snapshot load in `uniguru/ontology/snapshot_manager.py`.

Active constraints:
- exactly one root (`parent_id=null`)
- parent existence for all non-root nodes
- DFS cycle rejection
- allowed domain enforcement: `quantum`, `jain`, `swaminarayan`, `gurukul`, `core`
- duplicate concept id rejection

## 3) Snapshot Determinism
Implemented in `uniguru/ontology/snapshot_manager.py`.

Hashing now uses deterministic canonical encoding:
- `json.dumps(snapshot, sort_keys=True)` (excluding `snapshot_hash` field itself)
- SHA256 over canonical JSON bytes

Current replay snapshot:
- version: `1`
- hash: `e7292c6b78cfa8c7fe0008b36f6916879af5b9c78d763a3cbf402d3e3d6895ad`


## Merged: ONTOLOGY_SNAPSHOT_REPORT.md

# ONTOLOGY SNAPSHOT REPORT

## Snapshot ID: `v1`
**Status**: GENERATED & SEALED

The UniGuru Snapshot System ensures that the ontological state is deterministic and reproducible. Any deviation in the serialized state will cause a hash mismatch, failing the system.

### 1. Snapshot Parameters

- **Sorting Key**: `concept_id` (UUID)
- **Serialization Method**: Canonical JSON (Keys sorted, compact separators)
- **Hashing Algorithm**: SHA-256
- **Storage Path**: `uniguru/ontology/snapshots/snapshot_v1.json`

### 2. Snapshot Proof (JSON Header)

```json
{
  "snapshot_version": 1,
  "snapshot_hash": "7b01e6aca6b9552affc74df475aa3aa252dd23bc6f36020158ccae4589570586"
}
```

### 3. Deterministic Integrity Logic

The `SnapshotManager` in `uniguru/ontology/snapshot_manager.py` implements the following non-negotiable logic:

1. **Deterministic Order**: All concepts are sorted by `concept_id` before hashing to prevent nondeterministic dictionary iteration.
2. **Canonical JSON Generation**:
   - `sort_keys=True`
   - `separators=(",", ":")`
   - `ensure_ascii=True`
3. **SHA256 Integrity Seal**: The `snapshot_hash` is computed on the canonical representation of the snapshot version and the ordered concept list.

### 4. Replay Status

- **Hash Verified**: YES
- **Rebuilt Consistency**: IDENTICAL

Any modification to `snapshot_v1.json` without incrementing the `snapshot_version` will be caught during the next initialization or replay test.


## Merged: REPLAY_VALIDATION_REPORT.md

# REPLAY_VALIDATION_REPORT

## Deterministic Ontology Rebuild Validation
Validation source: `uniguru/ontology/replay_test.py`

Process:
1. Load snapshot (`snapshot_v1.json`)
2. Validate concept schema
3. Validate graph constraints (`OntologyGraph`)
4. Recompute canonical hash
5. Compare recomputed hash with stored hash

Observed result:
- `snapshot_version`: `1`
- `stored_hash`: `e7292c6b78cfa8c7fe0008b36f6916879af5b9c78d763a3cbf402d3e3d6895ad`
- `rebuilt_hash`: `e7292c6b78cfa8c7fe0008b36f6916879af5b9c78d763a3cbf402d3e3d6895ad`
- `replay_passed`: `true`

Conclusion:
- Snapshot rebuild is deterministic and replay-safe.


## Merged: SEMANTIC_DRIFT_REPORT.md

# SEMANTIC DRIFT REPORT

## Scope: ONTOLOGY EVOLUTION
**Status**: ACTIVE MONITORING

The UniGuru Semantic Drift Detector ensures that the ontology does not silently mutate or lose structural integrity during updates.

### 1. Drift Detection Rules (Strict)

| Rule Type | Violation Case | Action |
| :--- | :--- | :--- |
| **Parent Change** | `parent_id` mutation | Require `snapshot_version` bump. |
| **Truth Downgrade** | `truth_level` decrease | **REJECTED** (Non-negotiable). |
| **Canonical Name Mutation**| `canonical_name` change | Require `snapshot_version` bump. |

### 2. Violation Logic Implementation

The `drift_detector.py` in `uniguru/ontology/drift_detector.py` implements the following logic:

- **Truth Downgrades**: Any attempt to lower a `truth_level` for a known `concept_id` results in a total rejection of the snapshot update, regardless of the version.
- **Structural Shifts**: If a concept's `parent_id` or `canonical_name` changes, the `drift_detector` checks if `current_snapshot_version > previous_snapshot_version`. If not, a violation is recorded.
- **Silent Mutation Prevention**: Silent updates (changes without version increments) are blocked by the `version_bumped` check.

### 3. Current State Analysis

- **Current Version**: 1
- **Detected Drift**: NONE
- **Action**: All changes for v1 are locked. Any future `uniguru/ontology/graph.py` updates must increment `snapshot_version` to 2.

### 4. Enforcement Verdict

- **Integrity Status**: PASS
- **Silent Mutation Protection**: ENABLED
- **Authority Separation**: Only the UniGuru Registry can authoritatively determine drift status.


## Merged: GURUKUL_REGISTRY_ALIGNMENT.md

# GURUKUL REGISTRY ALIGNMENT REPORT

## Registry Contract: `UniGuru <=> Gurukul`
**Status**: ALIGNED & ENFORCED

This document defines the alignment between UniGuru (The Canonical Ontology Backbone) and Gurukul (The Consumer of Ontology).

### 1. Registry Contract Schema

Gurukul must consume the following payload for every ontological reference:

```json
{
  "concept_id": "UUID",
  "canonical_name": "string",
  "domain": "enum",
  "truth_level": "integer 0-4",
  "snapshot_version": "int",
  "snapshot_hash": "sha256"
}
```

### 2. RuleEngine Modification (Authority Separation)

Every answer emitted by the UniGuru `RuleEngine` now includes a mandatory `ontology_reference`. This reference is constructed by the `OntologyRegistry` and bound to the decision output.

#### Output Structure

```json
{
  "decision": "answer",
  "ontology_reference": {
    "concept_id": "adf9434a-c8b9-4f5d-9d4b-8b7e3c286028",
    "snapshot_version": 1,
    "snapshot_hash": "7b01e6aca6b9552affc74df475aa3aa252dd23bc6f36020158ccae4589570586"
  }
}
```

### 3. Gurukul Implementation (Adapter Alignment)

The `GurukulIntegrationAdapter` in `uniguru/integrations/gurukul/adapter.py` is the primary consumer. 

1. **Strict Consumption**: Gurukul consumes the `ontology_reference` and uses it to look up the full `registry_contract` from the `OntologyRegistry`.
2. **Authority Separation**:
   - Gurukul **cannot** override `truth_level`.
   - Gurukul **cannot** mutate `canonical_name`.
   - Gurukul **cannot** redefine the ontology `parent`.
3. **Sealing**: The `snapshot_hash` ensures that Gurukul is consuming the exact same version of the ontology that UniGuru is providing.

### 4. Alignment Verdict

- **Contract Integrity**: SECURE
- **Authority Separation Proof**: The `OntologyRegistry` acts as the single source of truth. Gurukul has no write access to the ontology state and acts solely as a consumer of verified concepts.
- **Fail-Closed**: Any mismatch in `snapshot_version` or `snapshot_hash` during registry lookup causes an immediate failure.
