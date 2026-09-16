from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("uniguru.integrations.tantra_ecosystem_bridge")

# InsightCore — confirmed endpoint: POST /auth/issue
# Swagger: https://insightcore-8tdt.onrender.com/docs#/default/issue_token_auth_issue_post
INSIGHT_CORE_URL = os.getenv("INSIGHT_CORE_URL", "https://insightcore-8tdt.onrender.com")
INSIGHT_CORE_CLIENT_ID = os.getenv("INSIGHT_CORE_CLIENT_ID", "")
INSIGHT_CORE_CLIENT_SECRET = os.getenv("INSIGHT_CORE_CLIENT_SECRET", "")

# InsightBridge
INSIGHT_BRIDGE_URL = os.getenv("INSIGHT_BRIDGE_URL", "https://insightbridge-phase-4-2-integration-demo.onrender.com")
INSIGHT_BRIDGE_TIMEOUT = float(os.getenv("INSIGHT_BRIDGE_TIMEOUT_SECONDS", "5.0"))

# Simple in-process token cache — avoids re-issuing JWT on every request
# Render free tier cold-starts can take 10-30s so we cache aggressively (55 min)
_TOKEN_CACHE: Dict[str, Any] = {"token": None, "expires_at": 0.0}
_TOKEN_TTL_SECONDS = 3300  # 55 minutes


def _get_jwt() -> Optional[str]:
    """
    Obtain a JWT from InsightCore POST /auth/issue.
    Caches the token for _TOKEN_TTL_SECONDS to avoid hammering the endpoint.
    Request body: { client_id, client_secret }
    Response body: { token: <jwt> }  (sovereign-core issuer, insight-bridge audience)
    """
    if not INSIGHT_CORE_CLIENT_ID or not INSIGHT_CORE_CLIENT_SECRET:
        logger.warning("InsightCore credentials not configured (INSIGHT_CORE_CLIENT_ID / INSIGHT_CORE_CLIENT_SECRET)")
        return None

    now = time.monotonic()
    if _TOKEN_CACHE["token"] and now < _TOKEN_CACHE["expires_at"]:
        return _TOKEN_CACHE["token"]

    try:
        resp = httpx.post(
            f"{INSIGHT_CORE_URL}/auth/issue",
            json={
                "client_id": INSIGHT_CORE_CLIENT_ID,
                "client_secret": INSIGHT_CORE_CLIENT_SECRET,
            },
            timeout=10.0,  # longer timeout — Render free tier cold start
        )
        resp.raise_for_status()
        body = resp.json()
        # Sovereign stack returns { "token": "..." }
        token = body.get("token") or body.get("access_token") or body.get("jwt")
        if token:
            _TOKEN_CACHE["token"] = token
            _TOKEN_CACHE["expires_at"] = now + _TOKEN_TTL_SECONDS
            logger.info("InsightCore JWT issued successfully (cached for %ds)", _TOKEN_TTL_SECONDS)
        else:
            logger.error("InsightCore /auth/issue returned no token field. Body keys: %s", list(body.keys()))
        return token
    except httpx.HTTPStatusError as exc:
        logger.error("InsightCore /auth/issue HTTP %s: %s", exc.response.status_code, exc.response.text[:200])
        return None
    except Exception as exc:
        logger.error("InsightCore JWT fetch failed: %s", exc)
        return None


def check_insightcore_health() -> Dict[str, Any]:
    """
    Verify InsightCore is reachable and credentials are valid.
    Returns a structured health result — safe to call from a health endpoint.
    """
    token = _get_jwt()
    return {
        "service": "insightcore",
        "url": INSIGHT_CORE_URL,
        "auth_endpoint": f"{INSIGHT_CORE_URL}/auth/issue",
        "credentials_configured": bool(INSIGHT_CORE_CLIENT_ID and INSIGHT_CORE_CLIENT_SECRET),
        "token_obtained": bool(token),
        "live": bool(token),
    }


def _ingest_to_bridge(payload: Dict[str, Any], token: Optional[str]) -> Dict[str, Any]:
    """POST telemetry payload to InsightBridge /ingest."""
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = httpx.post(
            f"{INSIGHT_BRIDGE_URL}/ingest",
            json=payload,
            headers=headers,
            timeout=INSIGHT_BRIDGE_TIMEOUT,
        )
        resp.raise_for_status()
        return {"live": True, "status": "ingested", "http_status": resp.status_code, "response": resp.json()}
    except httpx.HTTPStatusError as exc:
        logger.error("InsightBridge /ingest HTTP %s: %s", exc.response.status_code, exc.response.text[:200])
        return {"live": False, "status": "ingest_failed", "http_status": exc.response.status_code, "reason": exc.response.text[:200]}
    except Exception as exc:
        logger.error("InsightBridge ingest failed: %s", exc)
        return {"live": False, "status": "ingest_failed", "reason": str(exc)}


class TantraEcosystemFabric:
    """
    HTTP-based TANTRA ecosystem bridge.
    Flow: InsightCore POST /auth/issue → JWT → InsightBridge POST /ingest
    """

    def process_uniguru_event(
        self,
        query: str,
        trace_id: str,
        verification_status: str,
        event_type: str = "CURRICULUM_QUERY",
        extra_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        token = _get_jwt()

        bridge_payload = {
            "telemetry_data": {
                "request_id": trace_id,
                "path": "/ask",
                "method": "POST",
                "status_code": 200,
                "latency_ms": 0,
            },
            "metadata": {
                "user_id": "uniguru-runtime",
                "event_type": event_type,
                "verification_status": verification_status,
                "system": "uniguru",
            },
        }
        if extra_payload:
            bridge_payload["metadata"].update(extra_payload)

        result = _ingest_to_bridge(bridge_payload, token)
        result["trace_id"] = trace_id
        result["insightcore_auth"] = bool(token)
        return result


_fabric_instance: Optional[TantraEcosystemFabric] = None


def get_tantra_ecosystem_fabric() -> TantraEcosystemFabric:
    global _fabric_instance
    if _fabric_instance is None:
        _fabric_instance = TantraEcosystemFabric()
    return _fabric_instance
