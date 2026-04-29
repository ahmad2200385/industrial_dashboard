import asyncio

from core.config import settings
from core.logging import get_logger
from db.session import SessionLocal
from services.alert_service import AlertService
from services.websocket_service import ws_manager

logger = get_logger(__name__)


class AlertLifecycleManager:
    def __init__(self):
        self._task = None
        self._running = False

    def start(self):
        if self._task and not self._task.done():
            return

        self._running = True
        self._task = asyncio.create_task(self._expiry_loop())
        logger.info("Alert lifecycle manager started")

    async def stop(self):
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Alert lifecycle manager stopped")

    async def _expiry_loop(self):
        while self._running:
            db = SessionLocal()

            try:
                alert_service = AlertService()

                expired_alerts = alert_service.expire_due_alerts(db)

                for alert in expired_alerts:
                    await ws_manager.broadcast_alert(
                        AlertService.to_payload(alert),
                        action="expired",
                    )

            except Exception as exc:
                logger.exception("Alert expiry sweep failed: %s", exc)
                db.rollback()

            finally:
                db.close()

            await asyncio.sleep(
                max(settings.ALERT_EXPIRY_SWEEP_SECONDS, 1)
            )


alert_lifecycle_manager = AlertLifecycleManager()