from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.deps import get_db
from schemas import Alert, AlertCreate, AlertResolve
from services.alert_service import AlertService
from services.websocket_service import ws_manager

router = APIRouter(tags=['alerts'])
alert_service = AlertService()


@router.post('/alerts', response_model=Alert)
async def create_alert(alert: AlertCreate, db: Session = Depends(get_db)):
    db_alert = alert_service.create_alert(
        db,
        machine_id=alert.machine_id,
        alert_type=alert.alert_type,
        message=alert.message,
        level=alert.level,
    )
    await ws_manager.broadcast_alert(alert_service.to_payload(db_alert), action='created')
    return db_alert


@router.get('/alerts', response_model=list[Alert])
def read_alerts(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    return alert_service.list(db, skip=skip, limit=limit, active_only=active_only)


@router.post('/alerts/{alert_id}/resolve', response_model=Alert)
async def resolve_alert(alert_id: int, _payload: AlertResolve | None = None, db: Session = Depends(get_db)):
    db_alert = alert_service.resolve_alert(db, alert_id)
    await ws_manager.broadcast_alert(alert_service.to_payload(db_alert), action='resolved')
    return db_alert
