import uuid
from datetime import date, datetime, time, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_carnet_hmac, encrypt_pii
from app.models.carnet import Carnet
from app.models.tramite import Tramite
from app.models.turno import Turno
from app.models.user import User
from app.schemas.turno import TurnoResponse, TurnoResultadoRequest
from app.services.availability_service import LOCAL_TZ
from app.services.turno_service import turno_to_response


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
