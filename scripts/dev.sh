#!/usr/bin/env bash
# Development: run the backend (reload) and the Vite dev server together.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$ROOT/backend/.venv/bin/uvicorn" app.main:app \
  --reload --host 0.0.0.0 --port 8000 --app-dir "$ROOT/backend" &
BACKEND_PID=$!

(cd "$ROOT/frontend" && npm run dev) &
FRONTEND_PID=$!

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true' EXIT
wait
