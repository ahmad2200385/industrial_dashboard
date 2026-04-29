from fastapi import HTTPException
from sqlalchemy.orm import Session

from services.machine_service import MachineService
from services.redis_service import redis_manager


class CacheService:
    @staticmethod
    def get_cached_machine_data(db: Session, machine_id: int) -> dict:
        cached_data = redis_manager.get_cached_machine_data(machine_id)
        if cached_data:
            return {'cached': True, 'data': cached_data}

        machine_service = MachineService()
        machine = machine_service.get_or_404(db, machine_id)
        return {'cached': False, 'data': machine_service.to_payload(machine)}

    @staticmethod
    def get_sensor_history(machine_id: int, limit: int = 10) -> dict:
        history = redis_manager.get_cached_sensor_history(machine_id, limit)
        return {'machine_id': machine_id, 'history': history, 'count': len(history)}

    @staticmethod
    def get_machine_alerts(machine_id: int, limit: int = 10) -> dict:
        alerts = redis_manager.get_machine_alerts(machine_id, limit)
        return {'machine_id': machine_id, 'alerts': alerts, 'count': len(alerts)}

    @staticmethod
    def redis_health() -> dict:
        return redis_manager.health_check()

    @staticmethod
    def clear_cache(pattern: str = '*') -> dict:
        count = redis_manager.clear_cache(pattern)
        return {'message': f'Cleared {count} cache entries matching pattern: {pattern}'}
