import uuid
from datetime import datetime, time, timedelta, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agenda_configuracion import AgendaConfiguracion
from app.models.tramite import Tramite
from app.models.turno import Turno
from app.models.user import User
from app.schemas.turno import TurnoCreateRequest, TurnoResponse, TurnoUpdateRequest
from app.services.availability_service import AvailabilityService, LOCAL_TZ


class TurnoService:
    @classmethod
    def _to_response(cls, turno: Turno) -> TurnoResponse:
        ciudadano_nombre = f"{turno.ciudadano.nombre} {turno.ciudadano.apellido}" if turno.ciudadano else None
        tramite_nombre = turno.tramite.nombre if turno.tramite else None
        return TurnoResponse(
            id=turno.id,
            ciudadano_id=turno.ciudadano_id,
            ciudadano_nombre_completo=ciudadano_nombre,
            tramite_id=turno.tramite_id,
            tramite_nombre=tramite_nombre,
            fecha_hora_inicio=turno.fecha_hora_inicio,
            fecha_hora_fin=turno.fecha_hora_fin,
            estado=turno.estado,
            es_sobreturno=turno.es_sobreturno if turno.es_sobreturno is not None else False,
            sobreturno_prioridad=turno.sobreturno_prioridad,
            motivo_cancelacion=turno.motivo_cancelacion,
            cancelado_por_id=turno.cancelado_por_id,
            resultado_comentario=turno.resultado_comentario,
            variantes=list(turno.variantes) if turno.variantes else [],
            created_at=turno.created_at or datetime.now(timezone.utc),
        )

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
            elif data.datos_registro_inmediato:
                # Buscar o crear ciudadano
                pass  # En slice 9 se profundiza registro al vuelo; asignamos current_user.id si no

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

        # Lock con FOR UPDATE para prevenir condición de carrera
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

        # Fetch completo con relaciones para respuesta
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

        return cls._to_response(turno)

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
                stmt = stmt.join(Tramite).where(Tramite.area_id == area_id)
            if estado:
                filters.append(Turno.estado == estado)
            if es_sobreturno is not None:
                filters.append(Turno.es_sobreturno == es_sobreturno)

        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = stmt.order_by(Turno.fecha_hora_inicio.desc())
        res = await db.execute(stmt)
        turnos = res.scalars().all()
        return [cls._to_response(t) for t in turnos]

    @classmethod
    async def cancel_turno(
        cls,
        db: AsyncSession,
        current_user: User,
        turno_id: uuid.UUID,
        motivo_cancelacion: Optional[str] = None,
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
                status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado."
            )

        if current_user.rol.nombre == "CIUDADANO":
            if turno.ciudadano_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tiene permisos para cancelar este turno.",
                )
            # Regla de 24 horas de antelación
            ahora = datetime.now(timezone.utc)
            if turno.fecha_hora_inicio - ahora < timedelta(hours=24):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No puede cancelar un turno con menos de 24 horas de anticipación.",
                )
        else:
            if not motivo_cancelacion:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Debe ingresar obligatoriamente un motivo de cancelación.",
                )

        turno.estado = "CANCELADO"
        turno.cancelado_por_id = current_user.id
        if motivo_cancelacion:
            turno.motivo_cancelacion = motivo_cancelacion

        await db.commit()
        await db.refresh(turno)
        return cls._to_response(turno)

    @classmethod
    async def update_turno(
        cls,
        db: AsyncSession,
        current_user: User,
        turno_id: uuid.UUID,
        data: TurnoUpdateRequest,
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
                status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado."
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

            # Verificar cupo excluyendo el turno actual
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
        return cls._to_response(turno)
