#!/usr/bin/env bash
# MIRAGE one-time setup — Linux/macOS
# Installs: .venv + all Python deps + Playwright Chromium + web npm deps + .env
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== MIRAGE setup ==="

echo "[1/6] Checking prerequisites..."
python3 --version || { echo "Python 3.11+ required"; exit 1; }
node --version    || { echo "Node 18+ required"; exit 1; }
npm --version     || { echo "npm required"; exit 1; }

echo "[2/6] Creating virtualenv at .venv ..."
[ -d "$root/.venv" ] || python3 -m venv "$root/.venv"
pip="$root/.venv/bin/pip"
"$pip" install --upgrade pip --quiet

echo "[3/6] Installing Python dependencies (backend + target + mcp)..."
"$pip" install -r "$root/apps/backend/requirements.txt" \
               -r "$root/apps/target-merchant/requirements.txt" \
               -r "$root/apps/mcp-server/requirements.txt"

echo "[4/6] Installing Playwright Chromium..."
"$root/.venv/bin/playwright" install chromium

echo "[5/6] Installing web dependencies..."
(cd "$root/apps/web" && npm install)

echo "[6/6] Preparing .env ..."
if [ ! -f "$root/.env" ]; then
  cp "$root/.env.example" "$root/.env"
  echo "  created .env from .env.example (all sponsor keys blank = offline mode)"
else
  echo "  .env already exists — left untouched"
fi

echo "=== Setup complete. Run scripts/dev.sh to boot MIRAGE. ==="
