import uuid
from datetime import date, datetime, time, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_carnet_hmac, encrypt_pii, hash_dni_hmac, hash_password
from app.models.carnet import Carnet
from app.models.role import Role
from app.models.tramite import Tramite
from app.models.turno import Turno
from app.models.user import User
from app.models.variante import Variante
from app.schemas.turno import TurnoResponse, TurnoResultadoRequest, SobreturnoCreateRequest
from app.services.availability_service import LOCAL_TZ
from app.services.turno_service import TurnoService, turno_to_response


class OperationService:


    @classmethod
    async def get_cola_dia(
        cls,
        db: AsyncSession,
        fecha: Optional[date] = None,
        tramite_id: Optional[int] = None,
        area_id: Optional[int] = None,
    ) -> List[TurnoResponse]:
        if not fecha:
            fecha = datetime.now(LOCAL_TZ).date()

        start_dt = datetime.combine(fecha, time.min, tzinfo=LOCAL_TZ).astimezone(timezone.utc)
        end_dt = datetime.combine(fecha, time.max, tzinfo=LOCAL_TZ).astimezone(timezone.utc)

        stmt = (
            select(Turno)
            .options(
                selectinload(Turno.ciudadano),
                selectinload(Turno.tramite),
                selectinload(Turno.variantes),
            )
            .where(
                Turno.fecha_hora_inicio >= start_dt,
                Turno.fecha_hora_inicio <= end_dt,
            )
        )

        if tramite_id:
            stmt = stmt.where(Turno.tramite_id == tramite_id)

        if area_id:
            stmt = stmt.join(Turno.tramite).where(Tramite.area_id == area_id)

        result = await db.execute(stmt)
        turnos = result.scalars().all()

        regulares = [t for t in turnos if not t.es_sobreturno]
        sobreturnos = [t for t in turnos if t.es_sobreturno]

        regulares.sort(key=lambda t: t.fecha_hora_inicio)

        prio_map = {"ALTA": 1, "MEDIA": 2, "BAJA": 3}
        sobreturnos.sort(
            key=lambda t: (
                prio_map.get(t.sobreturno_prioridad or "BAJA", 4),
                t.created_at or datetime.now(timezone.utc),
            )
        )

        sorted_turnos = regulares + sobreturnos
        return [turno_to_response(t, include_pii=True) for t in sorted_turnos]

    @classmethod
    async def registrar_resultado_turno(
        cls,
        db: AsyncSession,
        turno_id: uuid.UUID,
        data: TurnoResultadoRequest,
        current_user: User,
    ) -> TurnoResponse:
        stmt = (
            select(Turno)
            .options(
                selectinload(Turno.ciudadano),
                selectinload(Turno.tramite),
                selectinload(Turno.variantes),
            )
            .where(Turno.id == turno_id)
            .with_for_update()
        )
        res = await db.execute(stmt)
        turno = res.scalar_one_or_none()

        if not turno:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Turno no encontrado.",
            )

        nuevo_estado = data.estado.upper()
        if nuevo_estado not in ("COMPLETO", "INCOMPLETO", "AUSENTE"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El estado resultado debe ser COMPLETO, INCOMPLETO o AUSENTE.",
            )

        if nuevo_estado == "INCOMPLETO":
            if not data.resultado_comentario or not data.resultado_comentario.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Debe ingresar obligatoriamente un comentario descriptivo al marcar como INCOMPLETO.",
                )

        if nuevo_estado == "COMPLETO" and turno.tramite and turno.tramite.emite_carnet:
            if not data.numero_carnet or not data.numero_carnet.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El número de carnet es obligatorio para trámites que emiten carnet.",
                )
            if not data.fecha_vencimiento:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La fecha de vencimiento es obligatoria para trámites que emiten carnet.",
                )

            try:
                venc_date = date.fromisoformat(data.fecha_vencimiento)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formato de fecha de vencimiento inválido. Use YYYY-MM-DD.",
                )

            if venc_date <= date.today():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La fecha de vencimiento debe ser posterior a la fecha actual.",
                )

            num_carnet_raw = data.numero_carnet.strip()
            num_carnet_cifrado = encrypt_pii(num_carnet_raw)
            num_carnet_hmac = hash_carnet_hmac(num_carnet_raw)

            carnet = Carnet(
                ciudadano_id=turno.ciudadano_id,
                tramite_id=turno.tramite_id,
                numero_carnet_cifrado=num_carnet_cifrado,
                numero_carnet_hmac=num_carnet_hmac,
                fecha_emision=date.today(),
                fecha_vencimiento=venc_date,
                activo=True,
            )
            db.add(carnet)

        turno.estado = nuevo_estado
        turno.resultado_comentario = data.resultado_comentario
        turno.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(turno)
        return turno_to_response(turno, include_pii=True)

    @classmethod
    async def crear_sobreturno(
        cls,
        db: AsyncSession,
        data: SobreturnoCreateRequest,
        current_user: User,
    ) -> TurnoResponse:
        tramite = await db.get(Tramite, data.tramite_id)
        if not tramite:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trámite no encontrado.",
            )

        try:
            fecha_obj = date.fromisoformat(data.fecha)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de fecha inválido. Use YYYY-MM-DD.",
            )

        start_dt = datetime.combine(fecha_obj, time.min, tzinfo=LOCAL_TZ).astimezone(timezone.utc)
        end_dt = datetime.combine(fecha_obj, time.max, tzinfo=LOCAL_TZ).astimezone(timezone.utc)

        stmt_count = select(Turno).where(
            Turno.tramite_id == data.tramite_id,
            Turno.es_sobreturno.is_(True),
            Turno.estado != "CANCELADO",
            Turno.fecha_hora_inicio >= start_dt,
            Turno.fecha_hora_inicio <= end_dt,
        )
        res_count = await db.execute(stmt_count)
        existing_sobreturnos = res_count.scalars().all()

        limite = tramite.limite_sobreturnos_diarios if tramite.limite_sobreturnos_diarios is not None else 5
        if len(existing_sobreturnos) >= limite:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Límite diario de sobreturnos alcanzado para esta fecha (Máximo {limite}).",
            )

        ciudadano_id = None
        if data.ciudadano_id:
            user = await db.get(User, data.ciudadano_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ciudadano no encontrado.",
                )
            ciudadano_id = user.id
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
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe especificar un ciudadano o proveer los datos para su registro inmediato.",
            )

        prio = (data.prioridad or "MEDIA").upper()
        if prio not in ("ALTA", "MEDIA", "BAJA"):
            prio = "MEDIA"

        variantes_objs = []
        if data.variante_ids:
            stmt_v = select(Variante).where(Variante.id.in_(data.variante_ids))
            res_v = await db.execute(stmt_v)
            variantes_objs = list(res_v.scalars().all())

        nuevo_turno = Turno(
            id=uuid.uuid4(),
            ciudadano_id=ciudadano_id,
            tramite_id=data.tramite_id,
            fecha_hora_inicio=start_dt,
            fecha_hora_fin=end_dt,
            estado="RESERVADO",
            es_sobreturno=True,
            sobreturno_prioridad=prio,
        )
        if variantes_objs:
            nuevo_turno.variantes = variantes_objs

        db.add(nuevo_turno)
        await db.commit()

        return await TurnoService.get_turno_by_id(db, current_user, nuevo_turno.id)

