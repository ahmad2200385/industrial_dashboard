$ErrorActionPreference = "Stop"

$mode = if ($args.Count -gt 0) { $args[0].ToLower() } else { "docker" }
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "[start.ps1] Mode: $mode"

if ($mode -eq "docker") {
    Set-Location $root
    docker compose up --build -d
    Write-Host "[start.ps1] Docker stack started."
    Write-Host "Frontend: http://localhost:3000"
    Write-Host "API:      http://localhost:8003"
    exit 0
}

if ($mode -eq "local") {
    $envFile = Join-Path $root "backend\.env"
    $envExample = Join-Path $root "backend\.env.example"
    if (-not (Test-Path $envFile) -and (Test-Path $envExample)) {
        Copy-Item $envExample $envFile
        Write-Host "[start.ps1] Created backend/.env from backend/.env.example"
    }

    Set-Location (Join-Path $root "backend")
    python -m pip install -r requirements.txt
    alembic upgrade head

    $backendLog = Join-Path $root "backend.local.log"
    $frontendLog = Join-Path $root "frontend.local.log"

    Start-Process -FilePath "python" -ArgumentList "-m uvicorn main:app --host 0.0.0.0 --port 8003 --reload" -RedirectStandardOutput $backendLog -RedirectStandardError $backendLog -WindowStyle Hidden

    Set-Location (Join-Path $root "frontend")
    npm.cmd install
    Start-Process -FilePath "npm.cmd" -ArgumentList "run dev -- --host 0.0.0.0 --port 3000" -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendLog -WindowStyle Hidden

    Write-Host "[start.ps1] Local services started in background."
    Write-Host "Frontend: http://localhost:3000"
    Write-Host "API:      http://localhost:8003"
    Write-Host "Logs:     backend.local.log, frontend.local.log"
    Write-Host "[start.ps1] Note: local mode expects PostgreSQL and Redis already running."
    exit 0
}

Write-Host "[start.ps1] Unknown mode: $mode"
Write-Host "Usage: .\start.ps1 [docker|local]"
exit 1
