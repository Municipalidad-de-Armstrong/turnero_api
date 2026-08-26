import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agenda_configuracion import AgendaConfiguracion
from app.models.tramite import Tramite
from app.models.turno import Turno
from app.models.user import User
from app.schemas.turno import TurnoResponse, TurnoUpdateRequest
from app.services.availability_service import (
    LOCAL_TZ,
    AvailabilityService,
    _min_booking_time,
)


class TurnoLifecycleService:
    @classmethod
    async def cancel_turno(
        cls,
        db: AsyncSession,
        current_user: User,
        turno_id: uuid.UUID,
        motivo_cancelacion: str | None = None,
    ) -> TurnoResponse:
        from app.services.turno_service import turno_to_response

        stmt = (
            select(Turno)
            .options(
                selectinload(Turno.ciudadano),
                selectinload(Turno.tramite).selectinload(Tramite.area),
                selectinload(Turno.variantes),
            )
            .where(Turno.id == turno_id)
        )
        res = await db.execute(stmt)
        turno = res.scalar_one_or_none()

        if not turno:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado."
            )

        if current_user.rol.nombre == "CIUDADANO":
            if turno.ciudadano_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tiene permisos para cancelar este turno.",
                )
            ahora = datetime.now(timezone.utc)
            if turno.fecha_hora_inicio - ahora < timedelta(hours=24):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No puede cancelar un turno con menos de 24 horas de anticipación.",
                )

        turno.estado = "CANCELADO"
        turno.cancelado_por_id = current_user.id
        turno.motivo_cancelacion = motivo_cancelacion.strip() if (motivo_cancelacion and motivo_cancelacion.strip()) else None

        await db.commit()
        await db.refresh(turno)
        return turno_to_response(turno)

    @classmethod
    async def update_turno(
        cls,
        db: AsyncSession,
        current_user: User,
        turno_id: uuid.UUID,
        data: TurnoUpdateRequest,
    ) -> TurnoResponse:
        from app.services.turno_service import turno_to_response

        stmt = (
            select(Turno)
            .options(
                selectinload(Turno.ciudadano),
                selectinload(Turno.tramite).selectinload(Tramite.area),
                selectinload(Turno.variantes),
            )
            .where(Turno.id == turno_id)
        )
        res = await db.execute(stmt)
        turno = res.scalar_one_or_none()

        if not turno:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado."
            )

        if turno.es_sobreturno and data.fecha_hora_inicio:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Los sobreturnos no poseen una franja horaria asignable y no se pueden reprogramar. Si es necesario, cancele el sobreturno y solicite uno nuevo.",
            )

        if current_user.rol.nombre == "CIUDADANO":
            if turno.ciudadano_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado."
                )
            if data.fecha_hora_inicio:
                ahora = datetime.now(timezone.utc)
                if turno.fecha_hora_inicio - ahora < timedelta(hours=24):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No puede reprogramar un turno con menos de 24 horas de anticipación.",
                    )
                min_booking = _min_booking_time()
                if data.fecha_hora_inicio < min_booking:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No se puede reprogramar un turno para el mismo día. Seleccione una fecha a partir de mañana.",
                    )

        if data.estado == "CANCELADO":
            return await cls.cancel_turno(
                db, current_user, turno_id, data.motivo_cancelacion
            )

        if data.fecha_hora_inicio or data.variante_ids:
            new_dt_start = data.fecha_hora_inicio or turno.fecha_hora_inicio
            variante_ids = (
                data.variante_ids
                if data.variante_ids is not None
                else [v.id for v in turno.variantes]
            )

            variantes = await AvailabilityService.validate_tramite_and_variantes(
                db, turno.tramite_id, variante_ids
            )
            duracion_total = sum(v.duracion_minutos for v in variantes) or 15
            new_dt_fin = new_dt_start + timedelta(minutes=duracion_total)

            turnos_stmt = (
                select(Turno)
                .where(
                    Turno.tramite_id == turno.tramite_id,
                    Turno.id != turno.id,
                    Turno.estado == "RESERVADO",
                    Turno.es_sobreturno.is_(False),
                    Turno.fecha_hora_inicio < new_dt_fin,
                    Turno.fecha_hora_fin > new_dt_start,
                )
                .with_for_update()
            )
            overlapping = list((await db.execute(turnos_stmt)).scalars().all())

            dt_local = new_dt_start.astimezone(LOCAL_TZ)
            db_weekday = AvailabilityService._python_to_db_weekday(dt_local.date())
            agenda_res = await db.execute(
                select(AgendaConfiguracion).where(
                    AgendaConfiguracion.tramite_id == turno.tramite_id,
                    AgendaConfiguracion.dia_semana == db_weekday,
                    AgendaConfiguracion.activo.is_(True),
                )
            )
            agenda = agenda_res.scalar_one_or_none()
            if not agenda:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El día seleccionado no cuenta con atención.",
                )

            if len(overlapping) >= agenda.capacidad_simultanea:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El horario elegido ya no posee cupo disponible.",
                )

            turno.fecha_hora_inicio = new_dt_start
            turno.fecha_hora_fin = new_dt_fin
            turno.variantes = variantes

        if data.resultado_comentario is not None:
            turno.resultado_comentario = data.resultado_comentario

        if data.estado and data.estado != turno.estado:
            turno.estado = data.estado

        await db.commit()
        await db.refresh(turno)
        return turno_to_response(turno)
