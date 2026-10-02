"""
BHIV MDU (Master Data Universe / Intelligence Data Universe Registry) client.

API Reference: https://bhiv-mdu-api.onrender.com/docs
OpenAPI Spec:  https://bhiv-mdu-api.onrender.com/api/v1/openapi.json
API Version:   1.0.0

Authentication:
    Set MDU_API_KEY environment variable. The API uses the X-API-Key header.
    No hardcoded tokens — all credentials must be injected via environment.

Configuration env vars:
    MDU_ENABLED          — "true" to enable live calls (default: "false")
    MDU_API_KEY          — X-API-Key authentication credential
    MDU_BASE_URL         — override base URL (default: https://bhiv-mdu-api.onrender.com)
    MDU_TIMEOUT_SECONDS  — HTTP request timeout (default: 10.0)

All endpoint paths are documented in the OpenAPI spec; no invented routes.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("uniguru.integrations.mdu_client")

# ---------------------------------------------------------------------------
# Canonical dataset IDs registered in the live BHIV MDU registry
# These are stable identifiers; the internal UUIDs are resolved at runtime.
# ---------------------------------------------------------------------------
UNIGURU_CANONICAL_ID = "BHIV-DS-UNIGURU-RUNTIME-001"

# Ecosystem canonical datasets that UniGuru references for lineage/replay
MDU_REPLAY_EVENTS_ID = "BHIV-DS-REPLAY-SEMANTIC-EVENTS-001"
MDU_LINEAGE_CHAIN_ID = "BHIV-DS-LINEAGE-CHAIN-001"
MDU_TRUST_PROPAGATION_ID = "BHIV-DS-TRUST-PROPAGATION-001"


# ---------------------------------------------------------------------------
# Enums — mirror the canonical OpenAPI enum values exactly
# ---------------------------------------------------------------------------

class TrustLevel(str, Enum):
    VERIFIED = "VERIFIED"
    TRUSTED = "TRUSTED"
    PROVISIONAL = "PROVISIONAL"
    UNVERIFIED = "UNVERIFIED"
    QUARANTINE = "QUARANTINE"


class DatasetStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"
    UNDER_REVIEW = "UNDER_REVIEW"


class ReplayCompatibility(str, Enum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    CONDITIONAL = "CONDITIONAL"
    NONE = "NONE"


class SimulationCompatibility(str, Enum):
    NATIVE = "NATIVE"
    COMPATIBLE = "COMPATIBLE"
    ADAPTABLE = "ADAPTABLE"
    INCOMPATIBLE = "INCOMPATIBLE"


class SchemaStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    RETIRED = "RETIRED"


# ---------------------------------------------------------------------------
# Request models — match DatasetRegisterRequest in the OpenAPI spec
# Required fields: canonical_id, dataset_name, source_system, owner_name,
#                  domain_primary
# ---------------------------------------------------------------------------

@dataclass
class IngestionReference:
    """Maps to IngestionReference schema."""
    system: str                       # required
    pipeline_id: Optional[str] = None
    frequency: Optional[str] = None
    last_ingested_at: Optional[str] = None  # ISO 8601 datetime string

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"system": self.system}
        if self.pipeline_id is not None:
            d["pipeline_id"] = self.pipeline_id
        if self.frequency is not None:
            d["frequency"] = self.frequency
        if self.last_ingested_at is not None:
            d["last_ingested_at"] = self.last_ingested_at
        return d


@dataclass
class DatasetRegisterRequest:
    """Maps to DatasetRegisterRequest schema.

    Required: canonical_id, dataset_name, source_system, owner_name,
              domain_primary
    """
    canonical_id: str
    dataset_name: str                 # minLength=3, maxLength=255
    source_system: str                # minLength=2, maxLength=255
    owner_name: str                   # minLength=2, maxLength=255
    domain_primary: str               # minLength=2, maxLength=100

    # Optional fields
    description: Optional[str] = None
    version: str = "1.0.0"
    source_location: Optional[str] = None
    owner_team: Optional[str] = None
    owner_contact: Optional[str] = None
    domain_tags: List[str] = field(default_factory=list)
    trust_level: TrustLevel = TrustLevel.UNVERIFIED
    replay_compatibility: ReplayCompatibility = ReplayCompatibility.NONE
    replay_notes: Optional[str] = None
    simulation_compatibility: SimulationCompatibility = SimulationCompatibility.INCOMPATIBLE
    simulation_notes: Optional[str] = None
    ingestion_reference: Optional[IngestionReference] = None
    extended_metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "canonical_id": self.canonical_id,
            "dataset_name": self.dataset_name,
            "source_system": self.source_system,
            "owner_name": self.owner_name,
            "domain_primary": self.domain_primary,
            "version": self.version,
            "domain_tags": self.domain_tags,
            "trust_level": self.trust_level.value,
            "replay_compatibility": self.replay_compatibility.value,
            "simulation_compatibility": self.simulation_compatibility.value,
        }
        if self.description is not None:
            d["description"] = self.description
        if self.source_location is not None:
            d["source_location"] = self.source_location
        if self.owner_team is not None:
            d["owner_team"] = self.owner_team
        if self.owner_contact is not None:
            d["owner_contact"] = self.owner_contact
        if self.replay_notes is not None:
            d["replay_notes"] = self.replay_notes
        if self.simulation_notes is not None:
            d["simulation_notes"] = self.simulation_notes
        if self.ingestion_reference is not None:
            d["ingestion_reference"] = self.ingestion_reference.to_dict()
        if self.extended_metadata is not None:
            d["extended_metadata"] = self.extended_metadata
        return d


@dataclass
class ProvenanceCreateRequest:
    """Maps to ProvenanceCreateRequest schema.

    event_type values (documented): ORIGIN | INGESTION | TRANSFORMATION |
                                    VALIDATION | TRUST_CHANGE | SCHEMA_CHANGE
    Required: event_type, recorded_by
    """
    event_type: str
    recorded_by: str

    source_system: Optional[str] = None
    source_reference: Optional[str] = None
    ingestion_pipeline: Optional[str] = None
    transformation_reference: Optional[Dict[str, Any]] = None
    trust_at_event: Optional[TrustLevel] = None
    notes: Optional[str] = None
    is_replay_safe: bool = False
    replay_context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "event_type": self.event_type,
            "recorded_by": self.recorded_by,
            "is_replay_safe": self.is_replay_safe,
        }
        if self.source_system is not None:
            d["source_system"] = self.source_system
        if self.source_reference is not None:
            d["source_reference"] = self.source_reference
        if self.ingestion_pipeline is not None:
            d["ingestion_pipeline"] = self.ingestion_pipeline
        if self.transformation_reference is not None:
            d["transformation_reference"] = self.transformation_reference
        if self.trust_at_event is not None:
            d["trust_at_event"] = self.trust_at_event.value
        if self.notes is not None:
            d["notes"] = self.notes
        if self.replay_context is not None:
            d["replay_context"] = self.replay_context
        return d


@dataclass
class TrustUpdateRequest:
    """Maps to TrustUpdateRequest schema.

    Required: trust_level, verified_by
    """
    trust_level: TrustLevel
    verified_by: str
    governance_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "trust_level": self.trust_level.value,
            "verified_by": self.verified_by,
        }
        if self.governance_notes is not None:
            d["governance_notes"] = self.governance_notes
        return d


# ---------------------------------------------------------------------------
# Response model — wraps the DatasetResponse from the API
# ---------------------------------------------------------------------------

@dataclass
class DatasetResponse:
    """Deserialized DatasetResponse from the BHIV MDU API."""
    id: str
    canonical_id: str
    dataset_name: str
    version: str
    status: str
    source_system: str
    owner_name: str
    domain_primary: str
    trust_level: str
    replay_compatibility: str
    simulation_compatibility: str
    registered_at: str
    updated_at: str

    # Optional / nullable fields
    description: Optional[str] = None
    source_location: Optional[str] = None
    owner_team: Optional[str] = None
    owner_contact: Optional[str] = None
    domain_tags: List[str] = field(default_factory=list)
    trust_verified_by: Optional[str] = None
    trust_verified_at: Optional[str] = None
    replay_notes: Optional[str] = None
    simulation_notes: Optional[str] = None
    schema_version: Optional[str] = None
    ingestion_reference: Optional[Dict[str, Any]] = None
    extended_metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DatasetResponse":
        return cls(
            id=d["id"],
            canonical_id=d["canonical_id"],
            dataset_name=d["dataset_name"],
            version=d["version"],
            status=d["status"],
            source_system=d["source_system"],
            owner_name=d["owner_name"],
            domain_primary=d["domain_primary"],
            trust_level=d["trust_level"],
            replay_compatibility=d["replay_compatibility"],
            simulation_compatibility=d["simulation_compatibility"],
            registered_at=d["registered_at"],
            updated_at=d["updated_at"],
            description=d.get("description"),
            source_location=d.get("source_location"),
            owner_team=d.get("owner_team"),
            owner_contact=d.get("owner_contact"),
            domain_tags=d.get("domain_tags") or [],
            trust_verified_by=d.get("trust_verified_by"),
            trust_verified_at=d.get("trust_verified_at"),
            replay_notes=d.get("replay_notes"),
            simulation_notes=d.get("simulation_notes"),
            schema_version=d.get("schema_version"),
            ingestion_reference=d.get("ingestion_reference"),
            extended_metadata=d.get("extended_metadata"),
        )


# ---------------------------------------------------------------------------
# MDU Client
# ---------------------------------------------------------------------------

class MDUClient:
    """
    Live client for the BHIV MDU (Intelligence Data Universe Registry).

    Auth:     X-API-Key header, sourced from MDU_API_KEY env var.
    Base URL: https://bhiv-mdu-api.onrender.com

    Documented endpoints used:
      GET   /api/v1/datasets/canonical/{canonical_id}   — lookup by canonical ID
      GET   /api/v1/datasets/{dataset_id}               — lookup by internal UUID
      POST  /api/v1/datasets/                            — register a dataset
      GET   /api/v1/datasets/{dataset_id}/provenance    — get provenance chain
      POST  /api/v1/datasets/{dataset_id}/provenance    — add provenance event
      GET   /api/v1/datasets/{dataset_id}/trust/history — trust history
      POST  /api/v1/datasets/{dataset_id}/trust         — update trust level
      GET   /api/v1/schemas/{schema_id}                 — get schema by UUID
      GET   /api/v1/schemas/dataset/{dataset_id}        — all schemas for dataset
      GET   /api/v1/discovery/summary                   — registry summary
      GET   /api/v1/discovery/replay-safe               — replay-safe datasets
      GET   /api/v1/discovery/trusted                   — trusted datasets
      GET   /health                                     — health check
    """

    BASE_URL = "https://bhiv-mdu-api.onrender.com"

    def __init__(self) -> None:
        self.enabled = (
            os.getenv("MDU_ENABLED", "false").strip().lower()
            in {"1", "true", "yes", "on"}
        )
        self.base_url = os.getenv("MDU_BASE_URL", self.BASE_URL).strip().rstrip("/")
        self.api_key = os.getenv("MDU_API_KEY", "").strip()
        self.timeout = float(os.getenv("MDU_TIMEOUT_SECONDS", "10.0"))

        if self.enabled and not self.api_key:
            logger.warning(
                "MDU_ENABLED=true but MDU_API_KEY is not set. "
                "Live MDU calls will be skipped. Set MDU_API_KEY to activate."
            )

    # ------------------------------------------------------------------
    # Public dataset operations
    # ------------------------------------------------------------------

    def get_dataset_by_canonical_id(
        self, canonical_id: str
    ) -> Dict[str, Any]:
        """
        GET /api/v1/datasets/canonical/{canonical_id}

        Returns a normalised result dict:
          {
            "live": bool,
            "status": int,          # HTTP status code (when live)
            "data": DatasetResponse | None,
            "raw": dict,            # raw API response body
            "reason": str,          # present on failure
          }
        """
        path = f"/api/v1/datasets/canonical/{canonical_id}"
        raw = self._get(path)
        return self._wrap_dataset_response(raw)

    def get_dataset_by_id(self, dataset_id: str) -> Dict[str, Any]:
        """
        GET /api/v1/datasets/{dataset_id}

        dataset_id is the internal UUID (not the canonical string ID).
        """
        path = f"/api/v1/datasets/{dataset_id}"
        raw = self._get(path)
        return self._wrap_dataset_response(raw)

    def register_dataset(
        self, request: DatasetRegisterRequest
    ) -> Dict[str, Any]:
        """
        POST /api/v1/datasets/

        Registers a new dataset. Returns 201 on success, 409 if the
        canonical_id already exists (idempotent: caller should handle 409
        by falling back to get_dataset_by_canonical_id).
        """
        raw = self._post("/api/v1/datasets/", request.to_dict())
        return self._wrap_dataset_response(raw)

    # ------------------------------------------------------------------
    # Provenance
    # ------------------------------------------------------------------

    def get_provenance(self, dataset_id: str) -> Dict[str, Any]:
        """GET /api/v1/datasets/{dataset_id}/provenance"""
        return self._get(f"/api/v1/datasets/{dataset_id}/provenance")

    def add_provenance(
        self, dataset_id: str, request: ProvenanceCreateRequest
    ) -> Dict[str, Any]:
        """POST /api/v1/datasets/{dataset_id}/provenance"""
        return self._post(
            f"/api/v1/datasets/{dataset_id}/provenance", request.to_dict()
        )

    # ------------------------------------------------------------------
    # Trust management
    # ------------------------------------------------------------------

    def update_trust(
        self, dataset_id: str, request: TrustUpdateRequest
    ) -> Dict[str, Any]:
        """POST /api/v1/datasets/{dataset_id}/trust"""
        return self._post(
            f"/api/v1/datasets/{dataset_id}/trust", request.to_dict()
        )

    def get_trust_history(self, dataset_id: str) -> Dict[str, Any]:
        """GET /api/v1/datasets/{dataset_id}/trust/history"""
        return self._get(f"/api/v1/datasets/{dataset_id}/trust/history")

    # ------------------------------------------------------------------
    # Schema operations
    # ------------------------------------------------------------------

    def get_schema(self, schema_id: str) -> Dict[str, Any]:
        """GET /api/v1/schemas/{schema_id}"""
        return self._get(f"/api/v1/schemas/{schema_id}")

    def get_schemas_for_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """GET /api/v1/schemas/dataset/{dataset_id}"""
        return self._get(f"/api/v1/schemas/dataset/{dataset_id}")

    # ------------------------------------------------------------------
    # Discovery endpoints
    # ------------------------------------------------------------------

    def get_registry_summary(self) -> Dict[str, Any]:
        """GET /api/v1/discovery/summary"""
        return self._get("/api/v1/discovery/summary")

    def get_replay_safe_datasets(
        self, domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """GET /api/v1/discovery/replay-safe"""
        path = "/api/v1/discovery/replay-safe"
        if domain:
            path = f"{path}?domain={urllib.request.quote(domain)}"
        return self._get(path)

    def get_trusted_datasets(
        self, domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """GET /api/v1/discovery/trusted"""
        path = "/api/v1/discovery/trusted"
        if domain:
            path = f"{path}?domain={urllib.request.quote(domain)}"
        return self._get(path)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        """GET /health"""
        return self._get("/health")

    # ------------------------------------------------------------------
    # UniGuru-specific composite helpers
    # ------------------------------------------------------------------

    def validate_schema(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify UniGuru's canonical dataset is registered and active in MDU.

        Resolves the dataset by canonical ID, then fetches its schemas.
        Returns a structured validation result.
        """
        result = self.get_dataset_by_canonical_id(UNIGURU_CANONICAL_ID)
        out: Dict[str, Any] = {
            "canonical_id": UNIGURU_CANONICAL_ID,
            "trace_id": payload.get("trace_id") or payload.get("evidence_id"),
        }
        if result.get("live") and result.get("data"):
            ds: DatasetResponse = result["data"]
            out["live"] = True
            out["dataset_id"] = ds.id
            out["dataset_status"] = ds.status
            out["trust_level"] = ds.trust_level
            out["schema_version"] = ds.schema_version
            # Fetch active schemas for this dataset
            schemas_result = self.get_schemas_for_dataset(ds.id)
            out["schemas"] = schemas_result.get("data")
        else:
            out["live"] = False
            out["reason"] = result.get("reason", "dataset_not_found")
        return out

    def validate_provenance(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify UniGuru's dataset provenance registration in MDU.

        Returns the DatasetResponse enriched with trace context from payload.
        """
        result = self.get_dataset_by_canonical_id(UNIGURU_CANONICAL_ID)
        out: Dict[str, Any] = {
            "canonical_id": UNIGURU_CANONICAL_ID,
            "trace_id": payload.get("trace_id"),
            "lineage_hash": payload.get("lineage_hash"),
            "runtime_hash": payload.get("runtime_hash"),
        }
        if result.get("live") and result.get("data"):
            ds: DatasetResponse = result["data"]
            out["live"] = True
            out["dataset_id"] = ds.id
            out["dataset_name"] = ds.dataset_name
            out["trust_level"] = ds.trust_level
            out["replay_compatibility"] = ds.replay_compatibility
            out["status"] = ds.status
        else:
            out["live"] = False
            out["reason"] = result.get("reason", "dataset_not_found")
        return out

    def validate_replay_lineage(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify that the ecosystem replay and lineage canonical datasets are
        accessible and replay-safe in MDU.
        """
        replay = self.get_dataset_by_canonical_id(MDU_REPLAY_EVENTS_ID)
        lineage = self.get_dataset_by_canonical_id(MDU_LINEAGE_CHAIN_ID)

        replay_ds: Optional[DatasetResponse] = replay.get("data")
        lineage_ds: Optional[DatasetResponse] = lineage.get("data")

        replay_live = bool(replay.get("live") and replay_ds)
        lineage_live = bool(lineage.get("live") and lineage_ds)

        return {
            "live": replay_live and lineage_live,
            "trace_id": payload.get("trace_id"),
            "replay_dataset": {
                "canonical_id": MDU_REPLAY_EVENTS_ID,
                "found": replay_live,
                "trust_level": replay_ds.trust_level if replay_ds else None,
                "replay_compatibility": replay_ds.replay_compatibility if replay_ds else None,
            },
            "lineage_dataset": {
                "canonical_id": MDU_LINEAGE_CHAIN_ID,
                "found": lineage_live,
                "trust_level": lineage_ds.trust_level if lineage_ds else None,
                "replay_compatibility": lineage_ds.replay_compatibility if lineage_ds else None,
            },
            "replay_compatible": (
                replay_ds.replay_compatibility == ReplayCompatibility.FULL.value
                if (replay_live and replay_ds)
                else False
            ),
        }

    def is_live(self) -> bool:
        """Return True if the client is configured and enabled."""
        return self.enabled and bool(self.api_key)

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
        }

    def _get(self, path: str) -> Dict[str, Any]:
        if not self.enabled or not self.api_key:
            return {"live": False, "reason": "not_configured", "path": path}
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url=url, headers=self._headers(), method="GET")
        return self._execute(req, path)

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled or not self.api_key:
            return {"live": False, "reason": "not_configured", "path": path}
        url = f"{self.base_url}{path}"
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        headers = {**self._headers(), "Content-Type": "application/json"}
        req = urllib.request.Request(url=url, data=body, headers=headers, method="POST")
        return self._execute(req, path)

    def _patch(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled or not self.api_key:
            return {"live": False, "reason": "not_configured", "path": path}
        url = f"{self.base_url}{path}"
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        headers = {**self._headers(), "Content-Type": "application/json"}
        req = urllib.request.Request(url=url, data=body, headers=headers, method="PATCH")
        return self._execute(req, path)

    def _execute(
        self, req: urllib.request.Request, path: str
    ) -> Dict[str, Any]:
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                data = json.loads(body) if body.strip() else {}
                return {"live": True, "status": resp.status, "raw": data, "path": path}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            logger.warning("MDU %s %s => %s: %s", req.method, path, exc.code, body[:300])
            try:
                raw = json.loads(body)
            except Exception:
                raw = {"detail": body[:300]}
            return {"live": False, "status": exc.code, "reason": body[:300], "raw": raw, "path": path}
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("MDU %s %s failed: %s", req.method, path, exc)
            return {"live": False, "reason": str(exc), "path": path}

    @staticmethod
    def _wrap_dataset_response(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upgrade a raw _get/_post result to include a typed DatasetResponse.

        Adds key "data": DatasetResponse | None alongside the "raw" body.
        """
        out = dict(raw)
        body = raw.get("raw")
        if raw.get("live") and isinstance(body, dict) and "id" in body:
            try:
                out["data"] = DatasetResponse.from_dict(body)
            except (KeyError, TypeError) as exc:
                logger.debug("Could not deserialise DatasetResponse: %s", exc)
                out["data"] = None
        else:
            out["data"] = None
        return out
