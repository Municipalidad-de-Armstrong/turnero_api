"""Cliente Redis compartido (singleton) para el backend.

Reutiliza un pool de conexiones global entre peticiones HTTP.
Configurado con `socket_connect_timeout` acotado (0.5s) para fallar rápidamente si
Redis no está activo en entorno local, y `socket_timeout` (2.0s) para soportar picos
de carga en producción sin falsos positivos.
"""

from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

_redis_client: Optional[aioredis.Redis] = None


def get_redis_client() -> aioredis.Redis:
    """Devuelve el cliente Redis global (singleton) con pool de conexiones."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=2.0,
            retry_on_timeout=False,
        )
    return _redis_client


async def close_redis_client() -> None:
    """Cierra el cliente/pool global al apagar la aplicación."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
