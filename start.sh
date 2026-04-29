#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-docker}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[start.sh] Mode: ${MODE}"

wait_api_ready() {
  local url="$1"
  local max_attempts="${2:-30}"
  local delay_seconds="${3:-2}"
  local attempt=1

  while [[ "${attempt}" -le "${max_attempts}" ]]; do
    if curl -fsS --max-time 3 "${url}" >/dev/null; then
      echo "[start.sh] API is ready: ${url}"
      return 0
    fi
    echo "[start.sh] Waiting for API (${attempt}/${max_attempts})..."
    sleep "${delay_seconds}"
    attempt=$((attempt + 1))
  done

  echo "[start.sh] API did not become ready in time: ${url}"
  return 1
}

if [[ "${MODE}" == "docker" ]]; then
  cd "${ROOT_DIR}"
  docker compose up --build -d
  if wait_api_ready "http://127.0.0.1:8003/"; then
    docker compose exec api python populate.py --machines 20 --create-missing --mode api --api-base-url http://127.0.0.1:8000
    echo "[start.sh] Telemetry data population completed (docker mode)."
  else
    echo "[start.sh] Skipping data population because API is not ready."
  fi
  echo "[start.sh] Docker stack started."
  echo "Frontend: http://localhost:3000"
  echo "API:      http://localhost:8003"
  exit 0
fi

if [[ "${MODE}" == "local" ]]; then
  if [[ ! -f "${ROOT_DIR}/backend/.env" && -f "${ROOT_DIR}/backend/.env.example" ]]; then
    cp "${ROOT_DIR}/backend/.env.example" "${ROOT_DIR}/backend/.env"
    echo "[start.sh] Created backend/.env from backend/.env.example"
  fi

  cd "${ROOT_DIR}/backend"
  python -m pip install -r requirements.txt
  alembic upgrade head
  nohup uvicorn main:app --host 0.0.0.0 --port 8003 --reload > "${ROOT_DIR}/backend.local.log" 2>&1 &

  cd "${ROOT_DIR}/frontend"
  npm install
  nohup npm run dev -- --host 0.0.0.0 --port 3000 > "${ROOT_DIR}/frontend.local.log" 2>&1 &

  cd "${ROOT_DIR}"
  if wait_api_ready "http://127.0.0.1:8003/"; then
    python backend/populate.py --machines 20 --create-missing --mode api --api-base-url http://127.0.0.1:8003
    echo "[start.sh] Telemetry data population completed (local mode)."
  else
    echo "[start.sh] Skipping data population because API is not ready."
  fi

  echo "[start.sh] Local services started in background."
  echo "Frontend: http://localhost:3000"
  echo "API:      http://localhost:8003"
  echo "Logs:     backend.local.log, frontend.local.log"
  echo "[start.sh] Note: local mode expects PostgreSQL and Redis already running."
  exit 0
fi

echo "[start.sh] Unknown mode: ${MODE}"
echo "Usage: ./start.sh [docker|local]"
exit 1
