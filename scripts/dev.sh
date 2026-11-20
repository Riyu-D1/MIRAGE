#!/usr/bin/env bash
# MIRAGE dev launcher — Linux/macOS
# Boots target-merchant (8001), backend (8000), web (3000) in parallel.
# Optional: uncomment the MCP line to also boot the tool server (8002).
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
py="$root/.venv/bin/python"

(cd "$root/apps/target-merchant" && "$py" -m uvicorn main:app --port 8001) &
(cd "$root/apps/backend" && "$py" -m uvicorn app.main:app --port 8000) &
(cd "$root/apps/web" && npm run dev) &
# (cd "$root/apps/mcp-server" && "$py" server.py) &

echo "MIRAGE services starting:"
echo "  Mission Control UI  ->  http://localhost:3000"
echo "  Backend API         ->  http://localhost:8000  (health: /api/health)"
echo "  Target Merchant     ->  http://localhost:8001  (health: /health)"
echo "  MCP server          ->  http://localhost:8002  (uncomment to enable)"

trap 'kill $(jobs -p) 2>/dev/null' EXIT
wait
