#!/usr/bin/env bash
# Run just the Vite dev server.
# The vite.config.ts already proxies /api → http://127.0.0.1:8000,
# so the backend must be running first (scripts/backend.sh).
# Usage: bash scripts/frontend.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND="$ROOT/frontend"

if [[ ! -d "$FRONTEND/node_modules" ]]; then
  echo "node_modules missing — running npm install..." >&2
  npm --prefix "$FRONTEND" install
fi

exec npm --prefix "$FRONTEND" run dev
