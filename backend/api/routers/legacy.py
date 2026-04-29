from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.deps import get_db
from services.machine_service import MachineService
from services.redis_service import redis_manager

router = APIRouter(tags=['legacy'])
machine_service = MachineService()


@router.post('/devices')
def create_device(name: str, location: str, db: Session = Depends(get_db)):
    machine = machine_service.create_machine(db, name=name, location=location)
    return machine_service.to_payload(machine)


@router.get('/devices')
def get_devices(db: Session = Depends(get_db)):
    machines = machine_service.list_machines(db)
    return [machine_service.to_payload(machine) for machine in machines]


@router.post('/device/{device_id}')
def update_device(device_id: int, temp: int):
    if redis_manager.client:
        redis_manager.client.set(f'device:{device_id}:temp', temp)
    return {'message': 'stored in redis'}


@router.get('/device/{device_id}')
def get_device(device_id: int):
    temp = redis_manager.client.get(f'device:{device_id}:temp') if redis_manager.client else None
    return {'temperature': temp}
