import json
from typing import Any, Dict, Optional

import redis

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


class RedisManager:
    def __init__(self, host: str, port: int, db: int):
        self.host = host
        self.port = port
        self.db = db
        self.client = None
        self.pubsub = None
        self.redis_available = False

        self.cache_ttl = {
            'machine_data': 3600,
            'latest_state': 300,
            'sensor_data': 300,
            'alerts': 86400,
        }

        self._connect()

    def _connect(self) -> None:
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            self.redis_available = bool(self.client.ping())
            if self.redis_available:
                self.pubsub = self.client.pubsub()
                logger.info('Redis connected on %s:%s/%s', self.host, self.port, self.db)
            else:
                logger.warning('Redis ping failed. Cache and pub/sub disabled.')
        except Exception as exc:
            logger.warning('Redis unavailable: %s', exc)
            self.client = None
            self.pubsub = None
            self.redis_available = False

    def ping(self) -> bool:
        if not self.client:
            return False
        try:
            self.redis_available = bool(self.client.ping())
            return self.redis_available
        except Exception:
            self.redis_available = False
            return False

    def _set_json(self, key: str, value: Dict[str, Any], ttl: int) -> bool:
        if not self.redis_available or not self.client:
            return False
        try:
            self.client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as exc:
            logger.error('Redis set_json failed for %s: %s', key, exc)
            return False

    def _get_json(self, key: str) -> Optional[Dict[str, Any]]:
        if not self.redis_available or not self.client:
            return None
        try:
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as exc:
            logger.error('Redis get_json failed for %s: %s', key, exc)
            return None

    def cache_machine_data(self, machine_id: int, data: Dict[str, Any]) -> bool:
        return self._set_json(f'machine:{machine_id}:latest', data, self.cache_ttl['machine_data'])

    def get_cached_machine_data(self, machine_id: int) -> Optional[Dict[str, Any]]:
        return self._get_json(f'machine:{machine_id}:latest')

    def cache_latest_state(self, machine_id: int, state: Dict[str, Any]) -> bool:
        return self._set_json(
            f'machine:{machine_id}:state:latest',
            state,
            self.cache_ttl['latest_state'],
        )

    def get_latest_state(self, machine_id: int) -> Optional[Dict[str, Any]]:
        return self._get_json(f'machine:{machine_id}:state:latest')

    def cache_sensor_data(self, machine_id: int, sensor_data: Dict[str, Any]) -> bool:
        if not self.redis_available or not self.client:
            return False
        try:
            self._set_json(f'machine:{machine_id}:sensor:latest', sensor_data, self.cache_ttl['sensor_data'])
            list_key = f'machine:{machine_id}:sensor:history'
            self.client.lpush(list_key, json.dumps(sensor_data))
            self.client.ltrim(list_key, 0, 99)
            self.client.expire(list_key, self.cache_ttl['sensor_data'])
            return True
        except Exception as exc:
            logger.error('cache_sensor_data failed: %s', exc)
            return False

    def get_cached_sensor_history(self, machine_id: int, limit: int = 10) -> list[Dict[str, Any]]:
        if not self.redis_available or not self.client:
            return []
        try:
            rows = self.client.lrange(f'machine:{machine_id}:sensor:history', 0, max(0, limit - 1))
            return [json.loads(item) for item in rows]
        except Exception as exc:
            logger.error('get_cached_sensor_history failed: %s', exc)
            return []

    def cache_alert(self, alert: Dict[str, Any]) -> bool:
        if not self.redis_available or not self.client:
            return False
        try:
            alert_id = alert.get('id')
            machine_id = alert.get('machine_id')
            if alert_id is None or machine_id is None:
                return False
            self._set_json(f'alert:{alert_id}', alert, self.cache_ttl['alerts'])
            list_key = f'machine:{machine_id}:alerts'
            self.client.lpush(list_key, str(alert_id))
            self.client.ltrim(list_key, 0, 49)
            self.client.expire(list_key, self.cache_ttl['alerts'])
            return True
        except Exception as exc:
            logger.error('cache_alert failed: %s', exc)
            return False

    def get_machine_alerts(self, machine_id: int, limit: int = 10) -> list[Dict[str, Any]]:
        if not self.redis_available or not self.client:
            return []
        try:
            alert_ids = self.client.lrange(f'machine:{machine_id}:alerts', 0, max(0, limit - 1))
            result: list[Dict[str, Any]] = []
            for alert_id in alert_ids:
                data = self._get_json(f'alert:{alert_id}')
                if data:
                    result.append(data)
            return result
        except Exception as exc:
            logger.error('get_machine_alerts failed: %s', exc)
            return []

    def publish(self, channel: str, payload: Dict[str, Any]) -> bool:
        if not self.redis_available or not self.client:
            return False
        try:
            self.client.publish(channel, json.dumps(payload))
            return True
        except Exception as exc:
            logger.error('publish to %s failed: %s', channel, exc)
            return False

    def publish_alert(self, alert: Dict[str, Any]) -> bool:
        machine_id = alert.get('machine_id')
        alert_type = alert.get('alert_type', 'unknown')
        ok = self.publish('alerts', alert)
        if machine_id is not None:
            ok = self.publish(f'machine:{machine_id}:alerts', alert) and ok
        ok = self.publish(f'alerts:{alert_type}', alert) and ok
        return ok

    def publish_sensor_data(self, sensor_data: Dict[str, Any]) -> bool:
        machine_id = sensor_data.get('machine_id')
        ok = self.publish('sensor_data', sensor_data)
        if machine_id is not None:
            ok = self.publish(f'machine:{machine_id}:sensor', sensor_data) and ok
        return ok

    def publish_machine_update(self, machine: Dict[str, Any], action: str) -> bool:
        payload = {'action': action, 'machine': machine}
        machine_id = machine.get('id')
        ok = self.publish('machine_updates', payload)
        if machine_id is not None:
            ok = self.publish(f'machine:{machine_id}:updates', payload) and ok
        return ok

    def clear_cache(self, pattern: str = '*') -> int:
        if not self.redis_available or not self.client:
            return 0
        try:
            keys = self.client.keys(pattern)
            if not keys:
                return 0
            return int(self.client.delete(*keys))
        except Exception as exc:
            logger.error('clear_cache failed: %s', exc)
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        if not self.redis_available or not self.client:
            return {}
        try:
            info = self.client.info()
            return {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory': info.get('used_memory_human', '0B'),
                'total_keys': self.client.dbsize(),
                'uptime_days': info.get('uptime_in_days', 0),
            }
        except Exception as exc:
            logger.error('get_cache_stats failed: %s', exc)
            return {}

    def health_check(self) -> Dict[str, Any]:
        return {'connection': self.ping(), 'stats': self.get_cache_stats()}


redis_manager = RedisManager(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
)

redis_client = redis_manager.client
