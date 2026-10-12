#!/usr/bin/env bash
# Run just the Python backend.
# Usage: bash scripts/backend.sh [--port 8000] [--host 127.0.0.1]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "No .venv found. Run 'python scripts/start.py --check' first to set it up." >&2
  exit 1
fi

exec "$PYTHON" "$ROOT/scripts/serve.py" "$@"
