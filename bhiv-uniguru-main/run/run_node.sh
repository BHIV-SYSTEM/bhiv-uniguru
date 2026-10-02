#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}/node-backend"

export NODE_BACKEND_PORT="${NODE_BACKEND_PORT:-8080}"
export UNIGURU_ASK_URL="${UNIGURU_ASK_URL:-http://127.0.0.1:8000/ask}"

exec npm start
