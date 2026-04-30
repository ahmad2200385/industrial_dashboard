# Smart Factory Industrial Dashboard

## 1. Clone Project
```bash
git clone https://github.com/ahmad2200385/industrial_dashboard.git
cd industrial_dashboard
```

## 2. Run with Docker (First)
```bash
docker compose up --build -d
```
### 3. Verify status
```bash
docker compose ps
```

### 4. Open app
- Frontend: `http://localhost:3000`
- API: `http://localhost:8003`
- API docs: `http://localhost:8003/api/docs`

### 5. Stop
```bash
docker compose down
```

## Important: Telemetry Auto-Population

`populate.py` now runs automatically in Docker using the dedicated `populate` service.

- Service starts after API health check.
- It runs in API mode with internal URL: `http://api:8000`.
- It continuously generates machine telemetry data.

Check simulator logs:
```bash
docker compose logs -f populate
```

## 6. Run Locally (Without Docker)
Make sure PostgreSQL and Redis are already running.

Backend:
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8003 --reload
```

Frontend (new terminal):
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 3000
```

## 7. Run `populate.py` (Manual)
From host:
```bash
python backend/populate.py --machines 20 --create-missing --mode api --api-base-url http://localhost:8003
```

##  8. Ports
- Frontend: `http://localhost:3000`
- API (host): `http://localhost:8003`
- API Docs: `http://localhost:8003/api/docs`
- API inside Docker container: `http://127.0.0.1:8000`

## 9. Start Scripts (Use at the End)
Use these only if you want one-command startup.

Linux/macOS:
```bash
./start.sh
./start.sh local
```

Windows PowerShell:
```powershell
.\start.ps1
.\start.ps1 local
```

## 9. Screenshots
### Overview
![Overview Dashboard](./screenshots/overview.png)

### Lines
![Lines View](./screenshots/lines.png)

### Analytics
![Analytics View](./screenshots/analytics.png)

## 10. Author
**Ahmad**  
Smart Factory Industrial Dashboard

## 11. License
This project is licensed under the **MIT License**.

For full details: [PROJECT_DETAILS.md](./PROJECT_DETAILS.md)
