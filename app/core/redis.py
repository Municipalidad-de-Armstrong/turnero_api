"""Cliente Redis compartido (singleton) para todo el backend.

Antes, `get_redis()` abría una conexión nueva (con `ping`) por cada petición y la
cerraba al finalizar. Eso añadía un handshake TCP + PING a cada request autenticado.
Aquí se crea un único cliente con su connection pool interno, que se reutiliza entre
peticiones y se cierra al apagar la aplicación (ver `app.main.lifespan`).
"""

from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

_redis_client: Optional[aioredis.Redis] = None


def get_redis_client() -> aioredis.Redis:
    """Devuelve el cliente Redis global, creándolo (lazy) en la primera invocación."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis_client() -> None:
    """Cierra el cliente/pool global. Se llama al apagar la app."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
