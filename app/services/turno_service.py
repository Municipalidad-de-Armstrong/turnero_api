import uuid
from datetime import datetime, time, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import decrypt_pii, encrypt_pii, hash_dni_hmac, hash_password
from app.models.agenda_configuracion import AgendaConfiguracion
from app.models.role import Role
from app.models.tramite import Tramite
from app.models.turno import Turno
from app.models.user import User
from app.schemas.turno import TurnoCreateRequest, TurnoResponse, TurnoUpdateRequest
from app.services.availability_service import (
    LOCAL_TZ,
    AvailabilityService,
    _min_booking_time,
)
from app.services.turno_lifecycle_service import TurnoLifecycleService


def turno_to_response(turno: Turno, include_pii: bool = False) -> TurnoResponse:
    c = turno.ciudadano
    t = turno.tramite
    dni_v = decrypt_pii(c.dni_cifrado) if (include_pii and c and c.dni_cifrado) else None
    ph_v = decrypt_pii(c.telefono_cifrado) if (include_pii and c and c.telefono_cifrado) else None
    return TurnoResponse(
        id=turno.id,
        ciudadano_id=turno.ciudadano_id,
        ciudadano_nombre_completo=f"{c.nombre} {c.apellido}" if c else None,
        ciudadano_dni=dni_v,
        ciudadano_telefono=ph_v,
        tramite_id=turno.tramite_id,
        tramite_nombre=t.nombre if t else None,
        emite_carnet=t.emite_carnet if t else None,
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
            elif data.datos_registro_inmediato:
                reg = data.datos_registro_inmediato
                dni_hmac_val = hash_dni_hmac(reg.dni)
                stmt_usr = select(User).where(User.dni_hmac == dni_hmac_val)
                res_usr = await db.execute(stmt_usr)
                usr = res_usr.scalar_one_or_none()
                if usr:
                    ciudadano_id = usr.id
                else:
                    stmt_role = select(Role).where(Role.nombre == "ciudadano")
                    role_res = await db.execute(stmt_role)
                    role = role_res.scalar_one_or_none()

                    new_user = User(
                        email=reg.email,
                        password_hash=hash_password(uuid.uuid4().hex),
                        nombre=reg.nombre,
                        apellido=reg.apellido,
                        dni_cifrado=encrypt_pii(reg.dni),
                        dni_hmac=dni_hmac_val,
                        telefono_cifrado=encrypt_pii(reg.telefono),
                        rol_id=role.id if role else 1,
                        estado="PENDING_VALIDATION",
                    )
                    db.add(new_user)
                    await db.flush()
                    ciudadano_id = new_user.id

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

        if current_user.rol.nombre == "CIUDADANO":
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

        from app.services.notification_service import (
            create_in_app_notification,
            send_whatsapp_notification,
        )
        t_resp = await cls.get_turno_by_id(db, current_user, nuevo_turno.id)
        tr_name = getattr(t_resp, "tramite_nombre", None)
        if not tr_name and hasattr(t_resp, "tramite") and t_resp.tramite:
            tr_name = t_resp.tramite.nombre
        tr_name = tr_name or "Trámite"
        dt_str = dt_inicio.strftime("%Y-%m-%d %H:%M")
        msg = f"Su turno para '{tr_name}' ha sido reservado para el {dt_str} hs."
        await create_in_app_notification(
            db, usuario_id=ciudadano_id, titulo="Turno Confirmado", mensaje=msg
        )
        c_phone = getattr(t_resp, "ciudadano_telefono", None)
        if c_phone:
            await send_whatsapp_notification(c_phone, msg)

        return t_resp



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

        is_owner_or_admin = (
            current_user.id == turno.ciudadano_id
            or current_user.rol.nombre in ["ADMINISTRATIVO", "ADMINISTRADOR"]
        )
        return turno_to_response(turno, include_pii=is_owner_or_admin)


    @classmethod
    async def list_turnos(
        cls,
        db: AsyncSession,
        current_user: User,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
        area_id: int | None = None,
        tramite_id: int | None = None,
        estado: str | None = None,
        es_sobreturno: bool | None = None,
        dni: str | None = None,
        search: str | None = None,
    ) -> list[TurnoResponse]:
        stmt = select(Turno).options(
            selectinload(Turno.ciudadano),
            selectinload(Turno.tramite),
            selectinload(Turno.variantes),
        )

        filters = []
        is_admin = current_user.rol.nombre in ["ADMINISTRATIVO", "ADMINISTRADOR"]

        if current_user.rol.nombre == "CIUDADANO":
            filters.append(Turno.ciudadano_id == current_user.id)
        else:
            if fecha_desde:
                filters.append(Turno.fecha_hora_inicio >= fecha_desde)
            if fecha_hasta:
                filters.append(Turno.fecha_hora_inicio <= fecha_hasta)
            if area_id:
                stmt = stmt.join(Turno.tramite).where(Tramite.area_id == area_id)
            if tramite_id:
                filters.append(Turno.tramite_id == tramite_id)
            if estado:
                filters.append(Turno.estado == estado)
            if es_sobreturno is not None:
                filters.append(Turno.es_sobreturno == es_sobreturno)
            if dni:
                dni_hmac_val = hash_dni_hmac(dni.strip())
                stmt = stmt.join(Turno.ciudadano).where(User.dni_hmac == dni_hmac_val)
            if search:
                pattern = f"%{search.strip()}%"
                if not dni:
                    stmt = stmt.join(Turno.ciudadano)
                filters.append(User.nombre.ilike(pattern) | User.apellido.ilike(pattern))

        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = stmt.order_by(Turno.fecha_hora_inicio.desc())
        res = await db.execute(stmt)
        turnos = res.scalars().all()
        return [turno_to_response(t, include_pii=is_admin) for t in turnos]

    @classmethod
    async def cancel_turno(
        cls,
        db: AsyncSession,
        current_user: User,
        turno_id: uuid.UUID,
        motivo_cancelacion: str | None = None,
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
