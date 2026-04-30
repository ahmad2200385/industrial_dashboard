#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-docker}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[start.sh] Mode: ${MODE}"

if [[ "${MODE}" == "docker" ]]; then
  cd "${ROOT_DIR}"
  docker compose up --build -d
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
