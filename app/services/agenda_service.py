import json
import logging
from typing import List
from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.redis import get_redis_client
from app.models.agenda_configuracion import AgendaConfiguracion
from app.models.tramite import Tramite
from app.schemas.agenda import AgendaConfigSaveItem, AgendaConfigResponse

logger = logging.getLogger(__name__)


class AgendaService:

    @staticmethod
    async def get_agenda_config(db: AsyncSession, tramite_id: int) -> List[AgendaConfiguracion]:
        tramite_res = await db.execute(select(Tramite).where(Tramite.id == tramite_id))
        if not tramite_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trámite con id {tramite_id} no encontrado",
            )

        redis_key = f"agenda_config:{tramite_id}"
        try:
            redis = await get_redis_client()
            cached_data = await redis.get(redis_key)
            if cached_data:
                items_dict = json.loads(cached_data)
                return [AgendaConfiguracion(**item) for item in items_dict]
        except Exception:
            if settings.is_production:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Servicio de caché no disponible.",
                )
            logger.warning("Redis caído en dev: lectura de caché agenda ignorada.", exc_info=True)

        result = await db.execute(
            select(AgendaConfiguracion)
            .where(AgendaConfiguracion.tramite_id == tramite_id)
            .order_by(AgendaConfiguracion.dia_semana)
        )
        items = list(result.scalars().all())

        try:
            redis = await get_redis_client()
            serialized = [
                AgendaConfigResponse.model_validate(item).model_dump() for item in items
            ]
            await redis.set(redis_key, json.dumps(serialized), ex=3600)
        except Exception:
            if settings.is_production:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Servicio de caché no disponible.",
                )
            logger.warning("Redis caído en dev: escritura de caché agenda ignorada.", exc_info=True)

        return items

    @staticmethod
    async def save_agenda_config(
        db: AsyncSession, tramite_id: int, data: List[AgendaConfigSaveItem]
    ) -> List[AgendaConfiguracion]:
        tramite_res = await db.execute(select(Tramite).where(Tramite.id == tramite_id))
        if not tramite_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trámite con id {tramite_id} no encontrado",
            )

        dias_vistos = set()
        for item in data:
            if item.dia_semana in dias_vistos:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El día de la semana {item.dia_semana} se encuentra duplicado en la solicitud",
                )
            dias_vistos.add(item.dia_semana)

        await db.execute(
            delete(AgendaConfiguracion).where(AgendaConfiguracion.tramite_id == tramite_id)
        )

        nuevos_registros = [
            AgendaConfiguracion(
                tramite_id=tramite_id,
                dia_semana=item.dia_semana,
                hora_inicio=item.hora_inicio,
                hora_fin=item.hora_fin,
                capacidad_simultanea=item.capacidad_simultanea,
                activo=item.activo,
            )
            for item in data
        ]
        db.add_all(nuevos_registros)
        await db.commit()

        try:
            redis = await get_redis_client()
            redis_key = f"agenda_config:{tramite_id}"
            await redis.delete(redis_key)
        except Exception:
            if settings.is_production:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Servicio de caché no disponible.",
                )
            logger.warning("Redis caído en dev: invalidación de caché agenda ignorada.", exc_info=True)

        result = await db.execute(
            select(AgendaConfiguracion)
            .where(AgendaConfiguracion.tramite_id == tramite_id)
            .order_by(AgendaConfiguracion.dia_semana)
        )
        return list(result.scalars().all())
