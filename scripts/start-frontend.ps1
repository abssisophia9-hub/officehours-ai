# Start the unified product app on Windows (port 5180).
# From repo root:
#   .\scripts\start-frontend.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$App = Join-Path $Root "frontend\officehours-app"

Set-Location $App
if (-not (Test-Path (Join-Path $App "node_modules"))) {
    npm ci
}

Write-Host "Product app : http://127.0.0.1:5180"
npm run dev -- --host 127.0.0.1 --port 5180
