from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.deps import get_db
from services.cache_service import CacheService

router = APIRouter(tags=['cache'])


@router.get('/machines/{machine_id}/cached')
def get_cached_machine_data(machine_id: int, db: Session = Depends(get_db)):
    return CacheService.get_cached_machine_data(db, machine_id)


@router.get('/machines/{machine_id}/sensor-history')
def get_sensor_history(machine_id: int, limit: int = 10):
    return CacheService.get_sensor_history(machine_id, limit)


@router.get('/machines/{machine_id}/alerts/cached')
def get_cached_machine_alerts(machine_id: int, limit: int = 10):
    return CacheService.get_machine_alerts(machine_id, limit)


@router.get('/redis/health')
def redis_health_check():
    return CacheService.redis_health()


@router.post('/redis/cache/clear')
def clear_redis_cache(pattern: str = '*'):
    return CacheService.clear_cache(pattern)
