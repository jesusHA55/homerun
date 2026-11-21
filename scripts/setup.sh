#!/usr/bin/env bash
# One-time setup: backend venv, frontend build, .env.
#
# On a Raspberry Pi the camera stack (libcamera + picamera2) only ships as apt
# packages, so the venv is created with --system-site-packages to see them:
#   sudo apt install -y python3-picamera2
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

VENV_ARGS=()
if python3 -c "import picamera2" 2>/dev/null; then
  echo "==> picamera2 found (system package); venv will use system site-packages"
  VENV_ARGS+=(--system-site-packages)
elif [ -e /proc/device-tree/model ] && grep -qi "raspberry pi" /proc/device-tree/model; then
  echo "!! Raspberry Pi without picamera2: run 'sudo apt install -y python3-picamera2' and re-run" >&2
fi

echo "==> Backend virtualenv"
python3 -m venv "${VENV_ARGS[@]}" "$ROOT/backend/.venv"
"$ROOT/backend/.venv/bin/pip" install --upgrade pip
"$ROOT/backend/.venv/bin/pip" install -e "$ROOT/backend"

echo "==> Frontend"
if command -v npm >/dev/null 2>&1; then
  cd "$ROOT/frontend"
  npm install
  npm run build
elif [ -f "$ROOT/frontend/dist/index.html" ]; then
  echo "npm not found; using the prebuilt frontend/dist"
else
  echo "!! npm not found and no frontend/dist: build it elsewhere (npm run build) and copy dist/ here" >&2
fi

echo "==> Environment file"
if [ ! -f "$ROOT/.env" ]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "created .env from .env.example"
fi

echo "Done. Edit .env, then run scripts/dev.sh (development) or scripts/install-service.sh (autostart)."
