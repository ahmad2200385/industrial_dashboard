#!/usr/bin/env sh
set -e

echo "[entrypoint] Waiting for PostgreSQL..."
python - <<'PY'
import os
import time
from sqlalchemy import create_engine, text

db_url = os.environ.get('DATABASE_URL')
if not db_url:
    raise SystemExit('DATABASE_URL is not set')

engine = create_engine(db_url, pool_pre_ping=True)
for i in range(60):
    try:
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        print('[entrypoint] PostgreSQL is ready')
        break
    except Exception as exc:
        if i == 59:
            raise
        time.sleep(2)
PY

echo "[entrypoint] Running migrations..."
alembic upgrade head

echo "[entrypoint] Starting API server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
