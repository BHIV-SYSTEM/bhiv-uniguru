/**
 * Sanskrit Decoder API Client
 *
 * Consumes:
 *   POST /v2/runtime/sanskrit/decode    → decode_sanskrit_concept()
 *   POST /v2/runtime/sanskrit/graph/traverse → traverse_concept_graph()
 *
 * Vijay's runtime API (backend/service/uniguru_runtime_api.py) serves these endpoints.
 * The backend URL is read from VITE_SANSKRIT_API_URL (defaults to the same origin as
 * the main API, port 8001 for the runtime API in local dev).
 */

import axios from "axios";
import type {
  SanskritDecoderApiResponse,
  GraphTraversalApiResponse,
} from "../types/sanskrit";

// ── URL resolution ─────────────────────────────────────────────────────────────
// Primary: VITE_SANSKRIT_API_URL (points to uniguru_runtime_api.py, typically :8001)
// Fallback: VITE_API_URL with port shifted to 8001
// Dev default: http://localhost:8001
const RUNTIME_API_BASE = (() => {
  const explicit = (import.meta.env?.VITE_SANSKRIT_API_URL as string | undefined)?.trim();
  if (explicit) return explicit.replace(/\/$/, "");
  const mainApi = (import.meta.env?.VITE_API_URL as string | undefined)?.trim();
  if (mainApi) {
    // If the main API is e.g. http://localhost:8000, try port 8001 for the runtime API
    return mainApi.replace(/:\d+$/, ":8001").replace(/\/$/, "");
  }
  return "http://localhost:8001";
})();

const client = axios.create({
  baseURL: RUNTIME_API_BASE,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

// ── decode ─────────────────────────────────────────────────────────────────────

export interface DecodeOptions {
  emitProof?: boolean;
  traceId?: string;
}

export async function decodeSanskritConcept(
  query: string,
  options: DecodeOptions = {}
): Promise<SanskritDecoderApiResponse> {
  const { emitProof = false, traceId } = options;
  const body: Record<string, unknown> = {
    query: query.trim(),
    emit_proof: emitProof,
  };
  if (traceId) body.trace_id = traceId;

  const response = await client.post<SanskritDecoderApiResponse>(
    "/v2/runtime/sanskrit/decode",
    body
  );
  return response.data;
}

// ── graph traverse ─────────────────────────────────────────────────────────────

export interface TraverseOptions {
  maxDepth?: number;
  edgeTypes?: string[];
  emitProof?: boolean;
}

export async function traverseConceptGraph(
  start: string,
  options: TraverseOptions = {}
): Promise<GraphTraversalApiResponse> {
  const { maxDepth = 3, edgeTypes, emitProof = false } = options;
  const body: Record<string, unknown> = {
    start: start.trim(),
    max_depth: maxDepth,
    emit_proof: emitProof,
  };
  if (edgeTypes && edgeTypes.length > 0) body.edge_types = edgeTypes;

  const response = await client.post<GraphTraversalApiResponse>(
    "/v2/runtime/sanskrit/graph/traverse",
    body
  );
  return response.data;
}

// ── health check ───────────────────────────────────────────────────────────────

export async function checkDecoderHealth(): Promise<{
  online: boolean;
  baseUrl: string;
}> {
  try {
    await client.get("/health", { timeout: 5_000 });
    return { online: true, baseUrl: RUNTIME_API_BASE };
  } catch {
    return { online: false, baseUrl: RUNTIME_API_BASE };
  }
}

export { RUNTIME_API_BASE };
