# Start the unified product app on Windows (port 5180).
# From repo root:
#   .\scripts\start-frontend.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$App = Join-Path $Root "frontend\officehours-app"

Set-Location $App
npm run dev
