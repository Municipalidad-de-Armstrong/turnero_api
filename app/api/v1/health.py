from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis_client, redis_kind

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check que reporta el estado real de DB y Redis por entorno.

    - **Producción**: valida Redis real (ping directo); si está offline, 503.
    - **Desarrollo**: reporta el backend activo (``real`` o ``memory``). Cuando
      se usa el mock en memoria, se considera ``online`` porque la funcionalidad
      que depende de Redis sí está disponible (aunque volátil).
    """
    db_status = "offline"
    redis_status = "offline"
    errors = []

    # Verify Database connection
    try:
        await db.execute(text("SELECT 1"))
        db_status = "online"
    except Exception as e:
        errors.append(f"Database error: {str(e)}")

    # Verify Redis connection
    if settings.is_production:
        # En prod, ping directo contra Redis real (no aceptamos mock).
        try:
            redis_client = aioredis.from_url(settings.redis_url)
            try:
                if await redis_client.ping():
                    redis_status = "online"
            finally:
                await redis_client.aclose()
        except Exception as e:
            errors.append(f"Redis error: {str(e)}")
    else:
        # En dev, reflejar el backend realmente en uso.
        try:
            client = await get_redis_client()
            kind = redis_kind()
            if kind == "memory":
                # Mock en memoria: reportar online con nota.
                if await client.ping():
                    redis_status = "online (mock)"
            elif kind == "real":
                if await client.ping():
                    redis_status = "online"
            else:
                errors.append("Redis error: cliente no inicializado.")
        except Exception as e:
            errors.append(f"Redis error: {str(e)}")

    unhealthy = db_status != "online" or not redis_status.startswith("online")
    if unhealthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "database": db_status,
                "redis": redis_status,
                "errors": errors,
            },
        )

    return {
        "status": "healthy",
        "database": db_status,
        "redis": redis_status,
    }
