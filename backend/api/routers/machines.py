"""Machine management API endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from common import ApplicationException
from db.deps import get_db
from schemas import Machine, MachineCreate, MachineUpdate
from services.machine_service import MachineService
from services.websocket_service import ws_manager

router = APIRouter(prefix="/machines", tags=["machines"])
machine_service = MachineService()


def _handle_exception(e: ApplicationException) -> HTTPException:
    """Convert application exception to HTTP exception."""
    return HTTPException(
        status_code=e.status_code,
        detail=e.to_dict(),
    )


@router.post("", response_model=Machine, status_code=status.HTTP_201_CREATED)
async def create_machine(
    machine: MachineCreate,
    db: Session = Depends(get_db),
) -> Machine:
    """Create a new machine."""
    try:
        db_machine = machine_service.create_machine(
            db,
            name=machine.name,
            location=machine.location,
        )
        await ws_manager.broadcast_machine_update(
            machine_service.to_payload(db_machine),
            "created",
        )
        return db_machine
    except ApplicationException as e:
        raise _handle_exception(e)


@router.get("", response_model=List[Machine])
def list_machines(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> List[Machine]:
    """List all machines."""
    try:
        return machine_service.list_machines(db, skip=skip, limit=limit)
    except ApplicationException as e:
        raise _handle_exception(e)


@router.get("/{machine_id}", response_model=Machine)
def read_machine(
    machine_id: int,
    db: Session = Depends(get_db),
) -> Machine:
    """Get machine by ID."""
    try:
        return machine_service.get_machine(db, machine_id)
    except ApplicationException as e:
        raise _handle_exception(e)


@router.put("/{machine_id}", response_model=Machine)
async def update_machine(
    machine_id: int,
    machine: MachineUpdate,
    db: Session = Depends(get_db),
) -> Machine:
    """Update machine."""
    try:
        update_data = machine.model_dump(exclude_unset=True)
        updated = machine_service.update_machine(db, machine_id, update_data)
        await ws_manager.broadcast_machine_update(
            machine_service.to_payload(updated),
            "updated",
        )
        return updated
    except ApplicationException as e:
        raise _handle_exception(e)


@router.delete("/{machine_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_machine(
    machine_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Delete machine."""
    try:
        machine = machine_service.get_machine(db, machine_id)
        machine_service.delete_machine(db, machine_id)
        await ws_manager.broadcast_machine_update(
            machine_service.to_payload(machine),
            "deleted",
        )
    except ApplicationException as e:
        raise _handle_exception(e)
