# Smart Factory Industrial Dashboard - Project Details

## Overview
This project is a full-stack industrial monitoring dashboard for smart factory operations.  
It simulates machine telemetry and visualizes line health, machine status, alerts, and trends in real time.

## Current Functional Scope
- Real-time machine monitoring with WebSocket updates
- Multi-view operations dashboard:
  - `Overview`
  - `Lines`
  - `Machines`
  - `Alerts`
  - `Analytics`
  - `Maintenance`
- Alert lifecycle handling (active, acknowledged/resolved, expired)
- Redis-assisted caching for fast operational reads
- CSV/PDF export actions from frontend
- Docker-first workflow with auto telemetry generation

## Technology Stack
- Backend: FastAPI, SQLAlchemy, Alembic, Redis
- Frontend: Vue 3 (Composition API), Vite
- Database: PostgreSQL
- Realtime: WebSocket + Redis pub/sub
- DevOps: Docker + Docker Compose

## Runtime Services (Docker Compose)
- `postgres`: primary relational store
- `redis`: cache + pub/sub
- `api`: FastAPI app, migrations on startup, serves REST + WebSocket
- `populate`: telemetry simulator (`populate.py`) running continuously in API mode
- `frontend`: production-built Vue app served via Nginx

## Backend Architecture
- `backend/api/routers`: route handlers (`machines`, `sensor_data`, `alerts`, `websocket`, etc.)
- `backend/services`: business logic (alerts, sensor processing, redis/websocket integration)
- `backend/db/repositories`: data access abstraction
- `backend/models`: SQLAlchemy models
- `backend/schemas`: Pydantic schemas for API contracts
- `backend/core`: config, middleware, logging
- `backend/alembic`: schema migration history
- `backend/populate.py`: synthetic telemetry generator

## Frontend Architecture
- `frontend/src/App.vue`: main SCADA-style dashboard shell and modules
- `frontend/src/composables/useFactoryDashboard.js`: central dashboard state and derived metrics
- `frontend/src/services/api.js`: HTTP client integration
- `frontend/src/services/websocket.js`: live subscription and reconnect behavior

## Data/Alert Flow
1. `populate` posts telemetry to `api` (`/sensor-data`) using `http://api:8000`.
2. API validates and stores records in PostgreSQL.
3. Alert logic evaluates thresholds and updates alert records.
4. Events are published and streamed via WebSocket.
5. Frontend updates tables/charts/status in near real time.

## UI Notes (Current)
- Line and machine views are both active operational views.
- Table alignment has been tuned so headers and values are visually consistent.
- Filtering/sorting controls drive the same machine/line dataset.

## Run Modes
- Docker mode: recommended and complete (includes auto-populate).
- Local mode: available for backend/frontend development with local PostgreSQL + Redis.

## Run Without Docker (Manual Setup)

### 1) Install prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+ (or compatible)
- Redis 6+ (or compatible)

### 2) Setup PostgreSQL
Create database and user (example):

```sql
CREATE DATABASE smart_factory;
CREATE USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE smart_factory TO postgres;
```

Default local connection example:
- Host: `localhost`
- Port: `5432`
- DB: `smart_factory`
- User: `postgres`
- Password: `postgres`

### 3) Setup Redis
Start Redis locally:
- Linux/macOS (service): `redis-server`
- Windows (Redis service/container): ensure it is reachable

Default Redis local values:
- Host: `localhost`
- Port: `6379`
- DB index: `0`

### 4) Configure backend environment
Create/update `backend/.env`:

```env
APP_ENV=development
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/smart_factory
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
AUTO_CREATE_SCHEMA=false
```

### 5) Run backend manually
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8003 --reload
```

### 6) Run frontend manually
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 3000
```

### 7) Optional manual telemetry simulation
```bash
python backend/populate.py --machines 20 --create-missing --mode api --api-base-url http://localhost:8003
```

## Manual Mode Troubleshooting

### PostgreSQL errors
- `password authentication failed`: verify username/password in `DATABASE_URL`.
- `connection refused`: PostgreSQL service not running or wrong port.
- `database "smart_factory" does not exist`: create DB first.

Quick check:
```bash
psql -h localhost -p 5432 -U postgres -d smart_factory
```

### Redis errors
- `Error 10061` / `connection refused`: Redis not running or wrong port.
- Wrong host in env: ensure `REDIS_HOST=localhost` for local mode.

Quick check:
```bash
redis-cli -h localhost -p 6379 ping
```
Expected response: `PONG`

### Backend migration/startup issues
- If `alembic upgrade head` fails, verify `DATABASE_URL` and DB permissions.
- If backend starts but dashboard is empty, run simulator command above.

### Frontend startup issues
- `vite is not recognized`: run `npm install` inside `frontend` first.
- Port conflict on `3000`: run with another port, for example:
```bash
npm run dev -- --host 0.0.0.0 --port 3001
```

### API URL confusion in manual mode
- Manual backend runs on `http://localhost:8003`
- Use this URL for simulator and frontend API config in local development

