# Starts the FastAPI server and the Streamlit demo UI together, and stops
# both cleanly on Ctrl+C.
#
# Usage:
#   .\run_demo.ps1
#
# Env vars (all optional):
#   API_PORT          default 8000
#   STREAMLIT_PORT     default 8501
#   FDC_API_KEY        required to start the API server; falls back to
#                      USDA's public DEMO_KEY (rate-limited) if unset
#
# Note: developed and tested on macOS/Linux via run_demo.sh; this
# PowerShell version is a best-effort port, not run against a live
# Windows box as part of this change.

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$ApiPort = if ($env:API_PORT) { $env:API_PORT } else { "8000" }
$StreamlitPort = if ($env:STREAMLIT_PORT) { $env:STREAMLIT_PORT } else { "8501" }

if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            if (-not (Get-Item "env:$name" -ErrorAction SilentlyContinue)) {
                [System.Environment]::SetEnvironmentVariable($name, $value)
            }
        }
    }
}

if (-not $env:FDC_API_KEY) {
    Write-Host "No FDC_API_KEY found (env var or .env) - using USDA's public DEMO_KEY (rate-limited)."
    Write-Host "Get your own free key: https://fdc.nal.usda.gov/api-key-signup"
    $env:FDC_API_KEY = "DEMO_KEY"
}

$env:SIMULATOR_API_BASE_URL = "http://localhost:$ApiPort"
$env:PYTHONPATH = "$RepoRoot\src;$env:PYTHONPATH"

Write-Host "Starting FastAPI server on http://localhost:$ApiPort ..."
$apiProcess = Start-Process -FilePath "uvicorn" `
    -ArgumentList "mind_recovery_mvp.main:app --host 127.0.0.1 --port $ApiPort" `
    -PassThru -NoNewWindow

Write-Host "Waiting for the server to become healthy..."
$healthy = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        Invoke-WebRequest -Uri "http://localhost:$ApiPort/health" -UseBasicParsing -TimeoutSec 2 | Out-Null
        $healthy = $true
        break
    } catch {
        Start-Sleep -Milliseconds 500
    }
}
if (-not $healthy) {
    Write-Host "Server did not become healthy in time - check the output above." -ForegroundColor Red
    Stop-Process -Id $apiProcess.Id -Force -ErrorAction SilentlyContinue
    exit 1
}
Write-Host "Server is up."

Write-Host "Starting Streamlit app on http://localhost:$StreamlitPort ..."
$streamlitProcess = Start-Process -FilePath "streamlit" `
    -ArgumentList "run streamlit_app.py --server.port $StreamlitPort" `
    -PassThru -NoNewWindow

Write-Host ""
Write-Host "Both running. Press Ctrl+C to stop."

try {
    Wait-Process -Id $apiProcess.Id, $streamlitProcess.Id
} finally {
    Write-Host "`nStopping..."
    Stop-Process -Id $apiProcess.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $streamlitProcess.Id -Force -ErrorAction SilentlyContinue
}
