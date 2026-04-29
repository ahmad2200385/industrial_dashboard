import asyncio
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from fastapi import WebSocket

from core.logging import get_logger
from services.redis_service import redis_manager

logger = get_logger(__name__)


@dataclass
class ConnectionState:
    reconnect_token: str
    subscriptions: Set[int] = field(default_factory=set)
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ResumeState:
    subscriptions: Set[int]
    expires_at: float


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, ConnectionState] = {}
        self.resume_sessions: Dict[str, ResumeState] = {}

        self.instance_id = str(uuid.uuid4())
        self.reconnect_ttl_seconds = 300

        self.realtime_channel = 'realtime.events'
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._listener_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def _prune_resume_sessions(self) -> None:
        now = time.time()
        expired = [token for token, state in self.resume_sessions.items() if state.expires_at <= now]
        for token in expired:
            self.resume_sessions.pop(token, None)

    async def connect(
        self,
        websocket: WebSocket,
        machine_ids: List[int] | None = None,
        reconnect_token: str | None = None,
    ) -> dict:
        await websocket.accept()
        self._prune_resume_sessions()

        subscriptions: Set[int] = set(machine_ids or [])
        token = reconnect_token or str(uuid.uuid4())

        if reconnect_token and reconnect_token in self.resume_sessions:
            restored = self.resume_sessions.pop(reconnect_token)
            subscriptions = set(restored.subscriptions)
            token = reconnect_token

        self.active_connections[websocket] = ConnectionState(
            reconnect_token=token,
            subscriptions=subscriptions,
        )

        welcome = {
            'type': 'connected',
            'reconnect_token': token,
            'subscriptions': sorted(subscriptions),
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        await websocket.send_json(welcome)

        logger.info('WebSocket connected. active=%s', len(self.active_connections))
        return welcome

    def disconnect(self, websocket: WebSocket):
        state = self.active_connections.pop(websocket, None)
        if state:
            self.resume_sessions[state.reconnect_token] = ResumeState(
                subscriptions=set(state.subscriptions),
                expires_at=time.time() + self.reconnect_ttl_seconds,
            )
            logger.info('WebSocket disconnected. active=%s', len(self.active_connections))

    async def resume_connection(self, websocket: WebSocket, reconnect_token: str) -> list[int] | None:
        self._prune_resume_sessions()
        state = self.active_connections.get(websocket)
        cached = self.resume_sessions.pop(reconnect_token, None)
        if not state or not cached:
            return None

        state.reconnect_token = reconnect_token
        state.subscriptions = set(cached.subscriptions)
        return sorted(state.subscriptions)

    async def subscribe_to_machine(self, websocket: WebSocket, machine_id: int):
        state = self.active_connections.get(websocket)
        if state:
            state.subscriptions.add(machine_id)

    async def unsubscribe_from_machine(self, websocket: WebSocket, machine_id: int):
        state = self.active_connections.get(websocket)
        if state:
            state.subscriptions.discard(machine_id)

    def get_subscriptions(self, websocket: WebSocket) -> list[int]:
        state = self.active_connections.get(websocket)
        if not state:
            return []
        return sorted(state.subscriptions)

    async def _broadcast_event(self, event: dict):
        message = {
            'type': event.get('event_type', 'unknown'),
            'data': event.get('data', {}),
            'timestamp': event.get('timestamp', datetime.now(timezone.utc).isoformat()),
        }
        if 'action' in event and event['action']:
            message['action'] = event['action']

        machine_id = event.get('machine_id')
        disconnected: list[WebSocket] = []

        for websocket, state in self.active_connections.items():
            if machine_id is None or not state.subscriptions or machine_id in state.subscriptions:
                try:
                    await websocket.send_json(message)
                except Exception as exc:
                    logger.warning('WebSocket send failed: %s', exc)
                    disconnected.append(websocket)

        for websocket in disconnected:
            self.disconnect(websocket)

    async def _emit_event(self, event_type: str, data: dict, machine_id: int | None = None, action: str | None = None):
        event = {
            'event_type': event_type,
            'data': data,
            'machine_id': machine_id,
            'action': action,
            'source': self.instance_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

        published = False
        if redis_manager.redis_available:
            published = redis_manager.publish(self.realtime_channel, event)

        if not published:
            await self._broadcast_event(event)

    async def broadcast_sensor_data(self, sensor_data: dict):
        machine_id = sensor_data['machine_id']
        redis_manager.publish_sensor_data(sensor_data)
        redis_manager.cache_sensor_data(machine_id, sensor_data)
        await self._emit_event('sensor_data', sensor_data, machine_id=machine_id)

    async def broadcast_alert(self, alert: dict, action: str | None = None):
        machine_id = alert['machine_id']
        redis_manager.publish_alert(alert)
        redis_manager.cache_alert(alert)
        await self._emit_event('alert', alert, machine_id=machine_id, action=action)

    async def broadcast_machine_update(self, machine: dict, action: str):
        redis_manager.publish_machine_update(machine, action)
        if action in {'created', 'updated'}:
            redis_manager.cache_machine_data(machine['id'], machine)
        await self._emit_event('machine_update', machine, machine_id=machine.get('id'), action=action)

    def start_pubsub_listener(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
        if not redis_manager.redis_available or not redis_manager.client:
            logger.warning('Redis unavailable. Running WebSocket fanout in single-instance mode.')
            return

        if self._listener_thread and self._listener_thread.is_alive():
            return

        self._stop_event.clear()
        self._listener_thread = threading.Thread(target=self._listen_pubsub, daemon=True)
        self._listener_thread.start()
        logger.info('Redis Pub/Sub listener started for channel: %s', self.realtime_channel)

    def stop_pubsub_listener(self):
        self._stop_event.set()
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=2)
        logger.info('Redis Pub/Sub listener stopped')

    def _listen_pubsub(self):
        pubsub = None
        try:
            pubsub = redis_manager.client.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe(self.realtime_channel)

            while not self._stop_event.is_set():
                message = pubsub.get_message(timeout=1.0)
                if not message:
                    continue

                raw_data = message.get('data')
                if not isinstance(raw_data, str):
                    continue

                try:
                    event = json.loads(raw_data)
                except json.JSONDecodeError:
                    logger.warning('Invalid realtime payload on Redis channel')
                    continue

                if self._loop and self._loop.is_running():
                    asyncio.run_coroutine_threadsafe(self._broadcast_event(event), self._loop)

        except Exception as exc:
            logger.exception('Redis Pub/Sub listener failed: %s', exc)
        finally:
            try:
                if pubsub:
                    pubsub.close()
            except Exception:
                pass


ws_manager = ConnectionManager()
