#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${ROOT_DIR}:${ROOT_DIR}/backend:${PYTHONPATH:-}"
export UNIGURU_HOST="${UNIGURU_HOST:-127.0.0.1}"
export UNIGURU_PORT="${UNIGURU_PORT:-8000}"
export UNIGURU_API_AUTH_REQUIRED="${UNIGURU_API_AUTH_REQUIRED:-false}"
export UNIGURU_LLM_URL="${UNIGURU_LLM_URL:-internal://demo-llm}"

exec python "${ROOT_DIR}/backend/main.py"
