import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.user import User
from app.schemas.turno import (
    SobreturnoCreateRequest,
    TurnoCreateRequest,
    TurnoResponse,
    TurnoResultadoRequest,
)
from app.services.operation_service import OperationService
from app.services.turno_service import TurnoService

router = APIRouter(prefix="/admin", tags=["admin-operation"])


@router.get(
    "/dashboard/cola",
    response_model=list[TurnoResponse],
    summary="Obtener la cola de atención del día con ordenamiento de regular y sobreturnos",
)
async def get_cola_dia(
    fecha: date | None = Query(None, description="Fecha de atención (YYYY-MM-DD). Por defecto la fecha actual."),
    tramite_id: int | None = Query(None, description="Filtro opcional por ID de trámite"),
    area_id: int | None = Query(None, description="Filtro opcional por ID de área"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMINISTRATIVO", "ADMINISTRADOR"])),
) -> list[TurnoResponse]:
    return await OperationService.get_cola_dia(
        db=db, fecha=fecha, tramite_id=tramite_id, area_id=area_id
    )


@router.post(
    "/sobreturnos",
    response_model=TurnoResponse,
    status_code=201,
    summary="Cargar un sobreturno con prioridad",
)
async def crear_sobreturno(
    data: SobreturnoCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMINISTRATIVO", "ADMINISTRADOR"])),
) -> TurnoResponse:
    return await OperationService.crear_sobreturno(
        db=db, data=data, current_user=current_user
    )


@router.post(
    "/turnos/manual",
    response_model=TurnoResponse,
    status_code=201,
    summary="Agendamiento manual presencial de turnos",
)
async def crear_turno_manual(
    data: TurnoCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMINISTRATIVO", "ADMINISTRADOR"])),
) -> TurnoResponse:
    return await TurnoService.create_turno(
        db=db, current_user=current_user, data=data
    )


@router.patch(
    "/turnos/{turno_id}/resultado",
    response_model=TurnoResponse,
    summary="Registrar resultado de atención (COMPLETO, INCOMPLETO, AUSENTE) y emisión de carnet",
)
async def registrar_resultado(
    turno_id: uuid.UUID,
    data: TurnoResultadoRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMINISTRATIVO", "ADMINISTRADOR"])),
) -> TurnoResponse:
    return await OperationService.registrar_resultado_turno(
        db=db, turno_id=turno_id, data=data, current_user=current_user
    )
