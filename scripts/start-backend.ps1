# Start the FastAPI backend on Windows (no uvicorn flags to retype).
# From repo root:
#   .\scripts\start-backend.ps1
#
# Copy backend\.env.example -> backend\.env and set GEMINI_API_KEY only.
# app.env_bootstrap loads that file at startup (process/CDN env still wins).

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Uvicorn = Join-Path $Backend "venv\Scripts\uvicorn.exe"
$EnvFile = Join-Path $Backend ".env"
$EnvExample = Join-Path $Backend ".env.example"

if (-not (Test-Path $Uvicorn)) {
    Write-Error "Missing backend\venv. Create it and pip install -r requirements.txt first."
}

if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Write-Host "Note: backend\.env missing. Copy backend\.env.example to backend\.env and set GEMINI_API_KEY."
    } else {
        Write-Host "Note: backend\.env missing. Create it before enabling Gemini."
    }
}

# Local FYP process defaults when unset (do not force LLM gates; those come from .env).
if (-not $env:OFFICEHOURS_DEMO) { $env:OFFICEHOURS_DEMO = "true" }
if (-not $env:OFFICEHOURS_CLUSTERING_BACKEND) { $env:OFFICEHOURS_CLUSTERING_BACKEND = "lexical" }
if (-not $env:OFFICEHOURS_REVISION_WEB) { $env:OFFICEHOURS_REVISION_WEB = "true" }

Set-Location $Backend
Write-Host "Backend API : http://127.0.0.1:8000"
Write-Host "Swagger UI  : http://127.0.0.1:8000/docs"
Write-Host "Demo mode   : $($env:OFFICEHOURS_DEMO)"
& $Uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
