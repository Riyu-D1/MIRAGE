# MIRAGE one-time setup — Windows PowerShell
# Installs: .venv + all Python deps + Playwright Chromium + web npm deps + .env
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "=== MIRAGE setup ===" -ForegroundColor Cyan

Write-Host "`n[1/6] Checking prerequisites..."
python --version
if ($LASTEXITCODE -ne 0) { throw "Python not found — install Python 3.11+ and re-run." }
node --version
if ($LASTEXITCODE -ne 0) { throw "Node not found — install Node 18+ and re-run." }
npm --version
if ($LASTEXITCODE -ne 0) { throw "npm not found." }

Write-Host "`n[2/6] Creating virtualenv at .venv ..."
if (-not (Test-Path "$root\.venv")) { python -m venv "$root\.venv" }
$pip = "$root\.venv\Scripts\pip.exe"
& $pip install --upgrade pip --quiet

Write-Host "`n[3/6] Installing Python dependencies (backend + target + mcp)..."
& $pip install -r "$root\apps\backend\requirements.txt" `
                 -r "$root\apps\target-merchant\requirements.txt" `
                 -r "$root\apps\mcp-server\requirements.txt"

Write-Host "`n[4/6] Installing Playwright Chromium..."
& "$root\.venv\Scripts\playwright.exe" install chromium

Write-Host "`n[5/6] Installing web dependencies..."
Push-Location "$root\apps\web"
npm install
Pop-Location

Write-Host "`n[6/6] Preparing .env ..."
if (-not (Test-Path "$root\.env")) {
  Copy-Item "$root\.env.example" "$root\.env"
  Write-Host "  created .env from .env.example (all sponsor keys blank = offline mode)"
} else {
  Write-Host "  .env already exists — left untouched"
}

Write-Host "`n=== Setup complete. Run scripts\dev.ps1 to boot MIRAGE. ===" -ForegroundColor Green
