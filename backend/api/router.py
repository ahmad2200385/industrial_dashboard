from fastapi import APIRouter

from api.routers import alerts, cache, health, legacy, machines, sensor_data, websocket

api_router = APIRouter()
api_router.include_router(websocket.router)
api_router.include_router(health.router)
api_router.include_router(machines.router)
api_router.include_router(sensor_data.router)
api_router.include_router(alerts.router)
api_router.include_router(cache.router)
api_router.include_router(legacy.router)
