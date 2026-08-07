import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.turno import TurnoCreateRequest, TurnoResponse, TurnoUpdateRequest
from app.services.turno_service import TurnoService

router = APIRouter()


@router.post(
    "",
    response_model=TurnoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reservar un turno regular",
)
async def create_turno(
    data: TurnoCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TurnoResponse:
    return await TurnoService.create_turno(db, current_user, data)


@router.get(
    "/mis-turnos",
    response_model=List[TurnoResponse],
    summary="Listar mis turnos (para ciudadano logueado)",
)
async def get_mis_turnos(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[TurnoResponse]:
    return await TurnoService.list_turnos(db, current_user)


@router.get(
    "",
    response_model=List[TurnoResponse],
    summary="Listar turnos con filtros",
)
async def list_turnos(
    fecha_desde: Optional[datetime] = Query(None),
    fecha_hasta: Optional[datetime] = Query(None),
    area_id: Optional[int] = Query(None),
    tramite_id: Optional[int] = Query(None),
    estado: Optional[str] = Query(None),
    es_sobreturno: Optional[bool] = Query(None),
    dni: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[TurnoResponse]:
    return await TurnoService.list_turnos(
        db,
        current_user,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        area_id=area_id,
        tramite_id=tramite_id,
        estado=estado,
        es_sobreturno=es_sobreturno,
        dni=dni,
        search=search,
    )


@router.get(
    "/{turno_id}",
    response_model=TurnoResponse,
    summary="Obtener detalle de un turno",
)
async def get_turno(
    turno_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TurnoResponse:
    return await TurnoService.get_turno_by_id(db, current_user, turno_id)


@router.patch(
    "/{turno_id}",
    response_model=TurnoResponse,
    summary="Actualizar o reprogramar un turno",
)
async def update_turno(
    turno_id: uuid.UUID,
    data: TurnoUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TurnoResponse:
    return await TurnoService.update_turno(db, current_user, turno_id, data)


@router.delete(
    "/{turno_id}",
    response_model=TurnoResponse,
    summary="Cancelar un turno",
)
async def cancel_turno(
    turno_id: uuid.UUID,
    motivo_cancelacion: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TurnoResponse:
    return await TurnoService.cancel_turno(
        db, current_user, turno_id, motivo_cancelacion=motivo_cancelacion
    )
