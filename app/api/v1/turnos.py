import uuid
from datetime import datetime

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
    response_model=list[TurnoResponse],
    summary="Listar mis turnos (para ciudadano logueado)",
)
async def get_mis_turnos(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TurnoResponse]:
    return await TurnoService.list_turnos(db, current_user)


@router.get(
    "",
    response_model=list[TurnoResponse],
    summary="Listar turnos con filtros",
)
async def list_turnos(
    fecha_desde: datetime | None = Query(None),
    fecha_hasta: datetime | None = Query(None),
    area_id: int | None = Query(None),
    tramite_id: int | None = Query(None),
    estado: str | None = Query(None),
    es_sobreturno: bool | None = Query(None),
    dni: str | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TurnoResponse]:
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
    motivo_cancelacion: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TurnoResponse:
    return await TurnoService.cancel_turno(
        db, current_user, turno_id, motivo_cancelacion=motivo_cancelacion
    )


@router.get(
    "/{turno_id}/planilla",
    summary="Obtener o descargar la planilla del turno en formato PDF",
)
async def get_planilla_turno(
    turno_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from fastapi import Response

    from app.services.pdf_service import generate_turno_planilla_pdf

    t_resp = await TurnoService.get_turno_by_id(db, current_user, turno_id)

    # Fetch Tramite object to get documentacion_requerida & requerimientos_previos
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.models.tramite import Tramite

    tram_res = await db.execute(
        select(Tramite).options(selectinload(Tramite.area)).where(Tramite.id == t_resp.tramite_id)
    )
    tramite_obj = tram_res.scalar_one_or_none()

    doc_req = tramite_obj.documentacion_requerida if tramite_obj else ""
    req_prev = tramite_obj.requerimientos_previos if tramite_obj else ""
    area_nombre = tramite_obj.area.nombre if (tramite_obj and tramite_obj.area) else "Municipalidad de Armstrong"
    variantes_str = ", ".join(v.nombre for v in t_resp.variantes) if t_resp.variantes else "Atención General"

    ciudadano_dni = t_resp.ciudadano_dni
    if not ciudadano_dni:
        from app.core.security import decrypt_pii
        from app.models.user import User
        c_res = await db.execute(select(User).where(User.id == t_resp.ciudadano_id))
        c_user = c_res.scalar_one_or_none()
        if c_user and c_user.dni_cifrado:
            ciudadano_dni = decrypt_pii(c_user.dni_cifrado)

    pdf_bytes = generate_turno_planilla_pdf(
        turno_id=str(t_resp.id),
        ciudadano_nombre=t_resp.ciudadano_nombre_completo or "Ciudadano",
        ciudadano_dni=ciudadano_dni or "Verificar en Ventanilla",
        tramite_nombre=t_resp.tramite_nombre or "Trámite Municipal",
        area_nombre=area_nombre,
        variantes_info=variantes_str,

        fecha_hora_inicio=t_resp.fecha_hora_inicio.strftime("%Y-%m-%d %H:%M"),
        fecha_hora_fin=t_resp.fecha_hora_fin.strftime("%H:%M"),
        documentacion_requerida=doc_req,
        requerimientos_previos=req_prev or "",
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=planilla_turno_{turno_id}.pdf"
        },
    )

