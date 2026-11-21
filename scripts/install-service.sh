#!/usr/bin/env bash
# Install and start the Homerun backend as a systemd service (autostart on boot).
# Run as the user that owns the checkout; uses sudo for the systemd parts.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_NAME="${SUDO_USER:-$(id -un)}"
UNIT=/etc/systemd/system/homerun-backend.service

[ -x "$ROOT/backend/.venv/bin/uvicorn" ] || { echo "run scripts/setup.sh first"; exit 1; }
[ -f "$ROOT/.env" ] || { echo "missing $ROOT/.env (copy .env.example)"; exit 1; }

sed -e "s|@USER@|$USER_NAME|g" -e "s|@ROOT@|$ROOT|g" \
  "$ROOT/scripts/homerun-backend.service" | sudo tee "$UNIT" >/dev/null

sudo systemctl daemon-reload
sudo systemctl enable homerun-backend.service
sudo systemctl restart homerun-backend.service
echo "Installed $UNIT (user=$USER_NAME, root=$ROOT)"
systemctl --no-pager --lines=5 status homerun-backend.service || true
