# Smart Factory System - Project Details

## What This Project Is
Smart Factory System is a full-stack industrial monitoring dashboard that simulates and visualizes real-time machine telemetry.

It is designed as an Industry 4.0 style project for learning, portfolio, and demonstration purposes.

## What It Does
- Monitors machines, sensor readings, and alerts in near real time.
- Streams live updates from backend to frontend using WebSockets.
- Shows operational views for:
  - `Overview`
  - `Lines`
  - `Machines`
  - `Alerts`
  - `Analytics`
  - `Maintenance`
- Supports alert lifecycle (active, resolved, expired).
- Caches recent operational data in Redis.
- Runs fully with Docker Compose or natively without Docker.
- Auto-populates demo telemetry data after startup scripts complete.

## Tech Stack
- Backend: FastAPI, SQLAlchemy, Alembic, Redis
- Frontend: Vue 3 (Composition API), Vite, Tailwind setup + custom dashboard styling
- Database: PostgreSQL
- Realtime: WebSocket + Redis Pub/Sub fanout
- Deployment/Dev Ops: Docker, Docker Compose

## Architecture Overview
- `backend/`
  - `api/routers`: REST + WebSocket routes
  - `services/`: business logic layer
  - `db/repositories`: data access layer
  - `models/`: SQLAlchemy models
  - `schemas/`: request/response validation models
  - `core/`: config, middleware, logging
  - `alembic/`: DB migrations
- `frontend/`
  - `src/App.vue`: main dashboard UI
  - `src/composables/useFactoryDashboard.js`: state/computed/actions
  - `src/services/api.js`: API client
  - `src/services/websocket.js`: WebSocket client/reconnect handling

## Core Features
- Machine CRUD operations
- Sensor data ingestion and listing
- Alert generation from telemetry thresholds
- Alert resolve/expire workflows
- Redis cache endpoints for machine snapshots/history
- CSV export and print-friendly report flow

## Realtime Data Flow
1. Telemetry is posted to backend (`/sensor-data`).
2. Backend stores in PostgreSQL.
3. Alert rules run and create alerts if needed.
4. Events are published to Redis and broadcast over WebSocket.
5. Frontend updates dashboard state instantly.

## Running the Project

### One-Command Start (Recommended)
Run from project root:

- Linux/macOS (Docker mode): `./start.sh`
- Windows PowerShell (Docker mode): `.\start.ps1`
- Linux/macOS (Local mode): `./start.sh local`
- Windows PowerShell (Local mode): `.\start.ps1 local`

Both scripts auto-start services, wait for API readiness, and run telemetry seeding automatically.

### Run Using Docker
1. Start:
   - `./start.sh` (Linux/macOS) or `.\start.ps1` (Windows)
2. Open:
   - Frontend: `http://localhost:3000`
   - API: `http://localhost:8003`
3. Stop:
   - `docker compose down`

### Run Locally (Without Docker)
1. Make sure PostgreSQL and Redis are already running.
2. Start:
   - `./start.sh local` (Linux/macOS) or `.\start.ps1 local` (Windows)
3. Open:
   - Frontend: `http://localhost:3000`
   - API: `http://localhost:8003`

## Telemetry Simulation
Startup scripts already run telemetry population automatically.
Use simulator commands below only for manual reseeding or extra data generation:

```bash
docker compose exec api python populate.py --machines 20 --create-missing --mode api --api-base-url http://127.0.0.1:8000
```

## Production Readiness Notes
This project is production-inspired and structured with proper layers, but still portfolio-focused.

Typical hardening steps before enterprise production:
- Add authentication/authorization
- Add stricter rate limits and security policies
- Add full test suite + CI checks
- Add monitoring/observability and SLO alerts
- Lock down admin cache endpoints

## Why This Project Is Valuable for Portfolio
- Demonstrates full-stack ownership.
- Shows realtime systems understanding.
- Uses clean backend layering and frontend state management.
- Shows Dockerized development workflow.
- Reflects practical industrial dashboard UI patterns.
