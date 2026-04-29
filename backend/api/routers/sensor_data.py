from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.logging import get_logger
from db.deps import get_db
from schemas import SensorData, SensorDataCreate
from services.alert_service import AlertService
from services.sensor_service import SensorService
from services.websocket_service import ws_manager

router = APIRouter(tags=['sensor-data'])
logger = get_logger(__name__)
sensor_service = SensorService()
alert_service = AlertService()


@router.post('/sensor-data', response_model=SensorData)
async def create_sensor_data(sensor_data: SensorDataCreate, db: Session = Depends(get_db)):
    try:
        db_sensor_data, alerts = sensor_service.create_sensor_data(
            db,
            machine_id=sensor_data.machine_id,
            temperature=sensor_data.temperature,
            status=sensor_data.status,
            production_count=sensor_data.production_count,
            timestamp=sensor_data.timestamp,
        )

        for alert in alerts:
            await ws_manager.broadcast_alert(alert_service.to_payload(alert), action='created')

        await ws_manager.broadcast_sensor_data(sensor_service.to_payload(db_sensor_data))
        return db_sensor_data
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception('Failed creating sensor data: %s', exc)
        db.rollback()
        raise HTTPException(status_code=500, detail='Failed to create sensor data')


@router.get('/sensor-data', response_model=list[SensorData])
def read_sensor_data(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return sensor_service.list_sensor_data(db, skip=skip, limit=limit)