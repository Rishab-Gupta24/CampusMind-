# CampusMind launcher (Windows PowerShell 5.1+). Double-click CampusMind.bat, or run:
#   powershell -ExecutionPolicy Bypass -File scripts\start.ps1 [-Rebuild] [-NoBrowser]
# Starts only what isn't already running: Ollama, the FastAPI backend (:8000), the Next.js app (:3000).
param(
    [switch]$Rebuild,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"
$LogDir = Join-Path $Backend "tmp"
New-Item -ItemType Directory -Force $LogDir | Out-Null

function Say($text) { Write-Host "  $text" }
function Ok($text) { Write-Host "  [ok] $text" -ForegroundColor Green }
function Warn($text) { Write-Host "  [!]  $text" -ForegroundColor Yellow }
function Fail($text) { Write-Host "  [x]  $text" -ForegroundColor Red; Read-Host "Press Enter to close"; exit 1 }

function Test-Url($url) {
    try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 $url | Out-Null; return $true } catch { return $false }
}

function Wait-Url($url, $seconds, $what) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Url $url) { return $true }
        Start-Sleep -Seconds 2
    }
    Fail "$what did not start within $seconds s. See the log in backend\tmp."
}

function Test-Port($port) {
    return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

Write-Host ""
Write-Host "CampusMind" -ForegroundColor Cyan
Write-Host ""

# ---- First-run checks ----
if (-not (Test-Path $Python)) { Fail "Backend not set up. In backend\ run: py -3.12 -m venv .venv ; .venv\Scripts\pip install -r requirements.txt" }
if (-not (Test-Path (Join-Path $Backend ".env"))) { Fail "backend\.env is missing. Copy backend\.env.example to backend\.env and add the Supabase URL and key." }
if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Say "Installing frontend packages (first run)..."
    Push-Location $Frontend; npm install --no-fund --no-audit | Out-Null; Pop-Location
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { Warn "ffmpeg not found on PATH: lecture uploads will fail." }

# ---- 1. Ollama (local AI) ----
if (Test-Url "http://127.0.0.1:11434/api/version") {
    Ok "Ollama is running"
    if ($env:OLLAMA_MAX_LOADED_MODELS -ne "2" -and [Environment]::GetEnvironmentVariable("OLLAMA_MAX_LOADED_MODELS", "User") -ne "2") {
        Say "Tip: if answers take ~25 s, set OLLAMA_MAX_LOADED_MODELS=2 (Windows environment variables) and restart Ollama."
    }
} else {
    if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) { Fail "Ollama is not installed. Get it from https://ollama.com" }
    Say "Starting Ollama..."
    $env:OLLAMA_MAX_LOADED_MODELS = "2"   # keep the LLM and the embedding model loaded together
    Start-Process -WindowStyle Hidden ollama -ArgumentList "serve" -RedirectStandardError (Join-Path $LogDir "ollama.log")
    Wait-Url "http://127.0.0.1:11434/api/version" 60 "Ollama" | Out-Null
    Ok "Ollama started (2 models stay loaded)"
}

# ---- 2. Backend ----
if (Test-Port 8000) {
    Ok "Backend already running on port 8000"
} else {
    Say "Starting the backend..."
    Start-Process -WindowStyle Hidden -WorkingDirectory $Backend $Python `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
        -RedirectStandardError (Join-Path $LogDir "uvicorn.log")
    Wait-Url "http://127.0.0.1:8000/api/health" 120 "The backend" | Out-Null
    Ok "Backend started"
}
try {
    $health = Invoke-RestMethod -TimeoutSec 5 "http://127.0.0.1:8000/api/health"
    if (-not $health.supabase) { Warn "Backend can't reach Supabase. Check backend\.env and your internet connection (or open the Supabase dashboard if the project is paused)." }
    if (-not $health.ollama) { Warn "Backend can't reach Ollama." }
    Say ("Knowledge base: {0} passages, answer model {1}" -f $health.chunks, $health.llm_model)
} catch { Warn "Couldn't read backend health." }

# ---- 3. App (Next.js production build) ----
$BuildId = Join-Path $Frontend ".next\BUILD_ID"
if (Test-Port 3000) {
    Ok "App already running on port 3000"
} else {
    if ($Rebuild -or -not (Test-Path $BuildId)) {
        Say "Building the app (first run takes about a minute)..."
        Push-Location $Frontend
        npm run build | Out-File -Encoding utf8 (Join-Path $LogDir "next-build.log")
        $code = $LASTEXITCODE
        Pop-Location
        if ($code -ne 0) { Fail "App build failed. See backend\tmp\next-build.log" }
    }
    Say "Starting the app..."
    Start-Process -WindowStyle Hidden -WorkingDirectory $Frontend cmd -ArgumentList "/c", "npm run start -- -p 3000 > `"$LogDir\next.log`" 2>&1"
    Wait-Url "http://localhost:3000" 60 "The app" | Out-Null
    Ok "App started"
}

Write-Host ""
Write-Host "  CampusMind is ready: http://localhost:3000" -ForegroundColor Cyan
Write-Host "  To install it as an app: open it in Chrome or Edge, then use 'Install CampusMind' in the address bar."
Write-Host "  To stop: run CampusMind-stop.bat"
Write-Host ""
if (-not $NoBrowser) { Start-Process "http://localhost:3000" }
