import uuid
from datetime import datetime, time, timedelta
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import decrypt_pii
from app.models.agenda_configuracion import AgendaConfiguracion
from app.models.tramite import Tramite
from app.models.turno import Turno
from app.models.user import User
from app.schemas.turno import TurnoCreateRequest, TurnoResponse, TurnoUpdateRequest
from app.services.availability_service import (
    AvailabilityService,
    LOCAL_TZ,
    _min_booking_time,
)
from app.services.turno_lifecycle_service import TurnoLifecycleService


def turno_to_response(turno: Turno, include_pii: bool = False) -> TurnoResponse:
    ciudadano_nombre = (
        f"{turno.ciudadano.nombre} {turno.ciudadano.apellido}"
        if turno.ciudadano
        else None
    )
    tramite_nombre = turno.tramite.nombre if turno.tramite else None
    emite_carnet = turno.tramite.emite_carnet if turno.tramite else None

    if include_pii:
        dni_val = (
            decrypt_pii(turno.ciudadano.dni_cifrado)
            if (turno.ciudadano and turno.ciudadano.dni_cifrado)
            else None
        )
        phone_val = (
            decrypt_pii(turno.ciudadano.telefono_cifrado)
            if (turno.ciudadano and turno.ciudadano.telefono_cifrado)
            else None
        )
    else:
        dni_val = None
        phone_val = None

    return TurnoResponse(
        id=turno.id,
        ciudadano_id=turno.ciudadano_id,
        ciudadano_nombre_completo=ciudadano_nombre,
        ciudadano_dni=dni_val,
        ciudadano_telefono=phone_val,
        tramite_id=turno.tramite_id,
        tramite_nombre=tramite_nombre,
        emite_carnet=emite_carnet,
        fecha_hora_inicio=turno.fecha_hora_inicio,
        fecha_hora_fin=turno.fecha_hora_fin,
        estado=turno.estado,
        es_sobreturno=turno.es_sobreturno if turno.es_sobreturno is not None else False,
        sobreturno_prioridad=turno.sobreturno_prioridad,
        motivo_cancelacion=turno.motivo_cancelacion,
        cancelado_por_id=turno.cancelado_por_id,
        resultado_comentario=turno.resultado_comentario,
        variantes=list(turno.variantes) if turno.variantes else [],
        created_at=turno.created_at,
    )


class TurnoService:

    @classmethod
    async def create_turno(
        cls, db: AsyncSession, current_user: User, data: TurnoCreateRequest
    ) -> TurnoResponse:
        variantes = await AvailabilityService.validate_tramite_and_variantes(
            db, data.tramite_id, data.variante_ids
        )

        ciudadano_id = current_user.id
        if current_user.rol.nombre in ["ADMINISTRATIVO", "ADMINISTRADOR"]:
            if data.ciudadano_id:
                ciudadano_id = data.ciudadano_id

        duracion_total = sum(v.duracion_minutos for v in variantes) or 15
        dt_inicio = data.fecha_hora_inicio
        dt_fin = dt_inicio + timedelta(minutes=duracion_total)

        dt_local = dt_inicio.astimezone(LOCAL_TZ)
        fecha_local = dt_local.date()
        hora_local = dt_local.time()

        db_weekday = AvailabilityService._python_to_db_weekday(fecha_local)
        agenda_stmt = select(AgendaConfiguracion).where(
            AgendaConfiguracion.tramite_id == data.tramite_id,
            AgendaConfiguracion.dia_semana == db_weekday,
            AgendaConfiguracion.activo.is_(True),
        )
        agenda_res = await db.execute(agenda_stmt)
        agenda = agenda_res.scalar_one_or_none()

        if not agenda:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay atención configurada para el día seleccionado.",
            )

        h_start = time.fromisoformat(agenda.hora_inicio)
        h_end = time.fromisoformat(agenda.hora_fin)
        fin_local = (dt_inicio + timedelta(minutes=duracion_total)).astimezone(LOCAL_TZ).time()

        if hora_local < h_start or fin_local > h_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El horario seleccionado está fuera del rango de atención de la agenda.",
            )

        min_booking = _min_booking_time()
        if dt_inicio < min_booking:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede reservar un turno para el mismo día. Seleccione una fecha a partir de mañana.",
            )

        turnos_stmt = (
            select(Turno)
            .where(
                Turno.tramite_id == data.tramite_id,
                Turno.estado == "RESERVADO",
                Turno.es_sobreturno.is_(False),
                Turno.fecha_hora_inicio < dt_fin,
                Turno.fecha_hora_fin > dt_inicio,
            )
            .with_for_update()
        )
        turnos_res = await db.execute(turnos_stmt)
        overlapping_turnos = list(turnos_res.scalars().all())

        if len(overlapping_turnos) >= agenda.capacidad_simultanea:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El horario seleccionado ya fue reservado por otro usuario. Por favor seleccione otro slot.",
            )

        nuevo_turno = Turno(
            id=uuid.uuid4(),
            ciudadano_id=ciudadano_id,
            tramite_id=data.tramite_id,
            fecha_hora_inicio=dt_inicio,
            fecha_hora_fin=dt_fin,
            estado="RESERVADO",
            es_sobreturno=False,
        )
        nuevo_turno.variantes = variantes

        db.add(nuevo_turno)
        await db.commit()
        await db.refresh(nuevo_turno)

        return await cls.get_turno_by_id(db, current_user, nuevo_turno.id)

    @classmethod
    async def get_turno_by_id(
        cls, db: AsyncSession, current_user: User, turno_id: uuid.UUID
    ) -> TurnoResponse:
        stmt = (
            select(Turno)
            .options(
                selectinload(Turno.ciudadano),
                selectinload(Turno.tramite),
                selectinload(Turno.variantes),
            )
            .where(Turno.id == turno_id)
        )
        res = await db.execute(stmt)
        turno = res.scalar_one_or_none()

        if not turno:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Turno no encontrado.",
            )

        if (
            current_user.rol.nombre == "CIUDADANO"
            and turno.ciudadano_id != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para acceder a este turno.",
            )

        return turno_to_response(turno)

    @classmethod
    async def list_turnos(
        cls,
        db: AsyncSession,
        current_user: User,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        area_id: Optional[int] = None,
        estado: Optional[str] = None,
        es_sobreturno: Optional[bool] = None,
    ) -> List[TurnoResponse]:
        stmt = select(Turno).options(
            selectinload(Turno.ciudadano),
            selectinload(Turno.tramite),
            selectinload(Turno.variantes),
        )

        filters = []
        if current_user.rol.nombre == "CIUDADANO":
            filters.append(Turno.ciudadano_id == current_user.id)
        else:
            if fecha_desde:
                filters.append(Turno.fecha_hora_inicio >= fecha_desde)
            if fecha_hasta:
                filters.append(Turno.fecha_hora_inicio <= fecha_hasta)
            if area_id:
                stmt = stmt.join(Turno.tramite).where(Tramite.area_id == area_id)
            if estado:
                filters.append(Turno.estado == estado)
            if es_sobreturno is not None:
                filters.append(Turno.es_sobreturno == es_sobreturno)

        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = stmt.order_by(Turno.fecha_hora_inicio.desc())
        res = await db.execute(stmt)
        turnos = res.scalars().all()
        return [turno_to_response(t) for t in turnos]

    @classmethod
    async def cancel_turno(
        cls,
        db: AsyncSession,
        current_user: User,
        turno_id: uuid.UUID,
        motivo_cancelacion: Optional[str] = None,
    ) -> TurnoResponse:
        return await TurnoLifecycleService.cancel_turno(
            db, current_user, turno_id, motivo_cancelacion
        )

    @classmethod
    async def update_turno(
        cls,
        db: AsyncSession,
        current_user: User,
        turno_id: uuid.UUID,
        data: TurnoUpdateRequest,
    ) -> TurnoResponse:
        return await TurnoLifecycleService.update_turno(
            db, current_user, turno_id, data
        )
