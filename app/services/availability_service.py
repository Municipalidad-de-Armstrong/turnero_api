from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agenda_configuracion import AgendaConfiguracion
from app.models.tramite import Tramite
from app.models.turno import Turno
from app.models.variante import Variante
from app.schemas.availability import BloqueDisponibilidad

LOCAL_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def _min_booking_time() -> datetime:
    now_local = datetime.now(LOCAL_TZ)
    now_plus_2h = now_local + timedelta(hours=2)
    tomorrow_midnight = datetime.combine(
        now_local.date() + timedelta(days=1), time(0, 0), tzinfo=LOCAL_TZ
    )
    return max(now_plus_2h, tomorrow_midnight).astimezone(timezone.utc)


class AvailabilityService:
    @staticmethod
    def _python_to_db_weekday(fecha: date) -> int:
        return (fecha.weekday() + 1) % 7

    @classmethod
    async def validate_tramite_and_variantes(
        cls, db: AsyncSession, tramite_id: int, variante_ids: list[int]
    ) -> list[Variante]:
        if not variante_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe seleccionar al menos una variante.",
            )

        tramite_stmt = select(Tramite).where(Tramite.id == tramite_id)
        tramite_res = await db.execute(tramite_stmt)
        tramite = tramite_res.scalar_one_or_none()
        if not tramite:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trámite no encontrado.",
            )

        var_stmt = select(Variante).where(Variante.id.in_(variante_ids))
        var_res = await db.execute(var_stmt)
        variantes = list(var_res.scalars().all())

        if len(variantes) != len(set(variante_ids)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Una o más variantes no existen.",
            )

        for var in variantes:
            if var.tramite_id != tramite_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Todas las variantes deben pertenecer al trámite seleccionado.",
                )

        return variantes

    @classmethod
    async def get_disponibilidad(
        cls,
        db: AsyncSession,
        tramite_id: int,
        fecha: date,
        variante_ids: list[int],
        for_admin: bool = False,
    ) -> list[BloqueDisponibilidad]:
        variantes = await cls.validate_tramite_and_variantes(
            db, tramite_id, variante_ids
        )
        duracion_total = sum(v.duracion_minutos for v in variantes) or 15

        db_weekday = cls._python_to_db_weekday(fecha)
        agenda_stmt = select(AgendaConfiguracion).where(
            AgendaConfiguracion.tramite_id == tramite_id,
            AgendaConfiguracion.dia_semana == db_weekday,
            AgendaConfiguracion.activo.is_(True),
        )
        agenda_res = await db.execute(agenda_stmt)
        agenda = agenda_res.scalar_one_or_none()

        if not agenda:
            return []

        h_start = time.fromisoformat(agenda.hora_inicio)
        h_end = time.fromisoformat(agenda.hora_fin)

        dt_start_local = datetime.combine(fecha, h_start, tzinfo=LOCAL_TZ)
        dt_end_local = datetime.combine(fecha, h_end, tzinfo=LOCAL_TZ)

        dt_start = dt_start_local.astimezone(timezone.utc)
        dt_end = dt_end_local.astimezone(timezone.utc)

        turnos_stmt = select(Turno).where(
            Turno.tramite_id == tramite_id,
            Turno.estado == "RESERVADO",
            Turno.es_sobreturno.is_(False),
            Turno.fecha_hora_inicio < dt_end,
            Turno.fecha_hora_fin > dt_start,
        )
        turnos_res = await db.execute(turnos_stmt)
        turnos = list(turnos_res.scalars().all())

        bloques: list[BloqueDisponibilidad] = []
        current_start = dt_start
        step = timedelta(minutes=15)
        duracion_td = timedelta(minutes=duracion_total)
        min_booking = datetime.now(timezone.utc) if for_admin else _min_booking_time()

        while current_start + duracion_td <= dt_end:
            slot_end = current_start + duracion_td
            overlapping = [
                t for t in turnos
                if t.fecha_hora_inicio < slot_end and t.fecha_hora_fin > current_start
            ]

            disponible = (
                current_start >= min_booking
                and len(overlapping) < agenda.capacidad_simultanea
            )
            bloques.append(
                BloqueDisponibilidad(
                    fecha_hora_inicio=current_start,
                    fecha_hora_fin=slot_end,
                    disponible=disponible,
                )
            )
            current_start += step

        return bloques

    @classmethod
    async def get_primer_turno_disponible(
        cls, db: AsyncSession, tramite_id: int, variante_ids: list[int]
    ) -> BloqueDisponibilidad:
        await cls.validate_tramite_and_variantes(db, tramite_id, variante_ids)
        today = datetime.now(LOCAL_TZ).date()
        min_booking = _min_booking_time()

        for day_offset in range(30):
            target_date = today + timedelta(days=day_offset)
            bloques = await cls.get_disponibilidad(
                db, tramite_id, target_date, variante_ids
            )
            for bloque in bloques:
                if bloque.disponible and bloque.fecha_hora_inicio >= min_booking:
                    return bloque

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay disponibilidad de turnos en los próximos 30 días.",
        )
