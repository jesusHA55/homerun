#!/usr/bin/env bash
# One-time setup: backend venv, frontend build, .env.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Backend virtualenv"
python3 -m venv "$ROOT/backend/.venv"
"$ROOT/backend/.venv/bin/pip" install --upgrade pip
"$ROOT/backend/.venv/bin/pip" install -e "$ROOT/backend"

echo "==> Frontend"
cd "$ROOT/frontend"
npm install
npm run build

echo "==> Environment file"
if [ ! -f "$ROOT/.env" ]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "created .env from .env.example"
fi

echo "Done. Edit .env, then run scripts/dev.sh (development) or install the systemd unit."
