# MIRAGE dev launcher — Windows PowerShell
# Boots target-merchant (8001), backend (8000), web (3000) in separate windows.
# Optional: uncomment the MCP line to also boot the Grok Bot tool server (8002).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = "$root\.venv\Scripts\python.exe"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\apps\target-merchant'; & '$py' -m uvicorn main:app --port 8001"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\apps\backend'; & '$py' -m uvicorn app.main:app --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\apps\web'; npm run dev"
# Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\apps\mcp-server'; & '$py' server.py"

Write-Host "MIRAGE services starting:" -ForegroundColor Cyan
Write-Host "  Mission Control UI  ->  http://localhost:3000"
Write-Host "  Backend API         ->  http://localhost:8000  (health: /api/health)"
Write-Host "  Target Merchant     ->  http://localhost:8001  (health: /health)"
Write-Host "  MCP server          ->  http://localhost:8002  (uncomment to enable)"
