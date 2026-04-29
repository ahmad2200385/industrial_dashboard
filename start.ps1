$ErrorActionPreference = "Stop"

$mode = if ($args.Count -gt 0) { $args[0].ToLower() } else { "docker" }
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "[start.ps1] Mode: $mode"

function Wait-ApiReady {
    param(
        [string]$Url,
        [int]$MaxAttempts = 30,
        [int]$DelaySeconds = 2
    )

    for ($i = 1; $i -le $MaxAttempts; $i++) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 | Out-Null
            Write-Host "[start.ps1] API is ready: $Url"
            return $true
        }
        catch {
            Write-Host "[start.ps1] Waiting for API ($i/$MaxAttempts)..."
            Start-Sleep -Seconds $DelaySeconds
        }
    }

    Write-Host "[start.ps1] API did not become ready in time: $Url"
    return $false
}

if ($mode -eq "docker") {
    Set-Location $root
    docker compose up --build -d
    if (Wait-ApiReady -Url "http://127.0.0.1:8003/") {
        docker compose exec api python populate.py --machines 20 --create-missing --mode api --api-base-url http://127.0.0.1:8000
        Write-Host "[start.ps1] Telemetry data population completed (docker mode)."
    }
    else {
        Write-Host "[start.ps1] Skipping data population because API is not ready."
    }
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

    Set-Location $root
    if (Wait-ApiReady -Url "http://127.0.0.1:8003/") {
        python backend/populate.py --machines 20 --create-missing --mode api --api-base-url http://127.0.0.1:8003
        Write-Host "[start.ps1] Telemetry data population completed (local mode)."
    }
    else {
        Write-Host "[start.ps1] Skipping data population because API is not ready."
    }

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
