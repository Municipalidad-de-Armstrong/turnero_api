"""Cliente Redis compartido (singleton) para el backend.

Estrategia por entorno:

- **Producción**: Redis es obligatorio. Si no responde, la app NO arranca
  (validado en ``app.main.lifespan``) y los errores en runtime se **propagan**
  en lugar de tragarse silenciosamente. Nunca se entrega un mock en producción.
- **Desarrollo**: si no hay Redis alcanzable, se usa un mock en memoria
  (``InMemoryRedis``) que implementa el subconjunto de la API que usa la app
  (``setex``, ``set``, ``get``, ``delete``, ``exists``, ``expire``, ``ping``)
  con soporte de TTL. Así logout / blacklist / reset-password funcionan E2E
  sin instalar nada localmente.

El selector de cliente vive en ``get_redis_client()``; el resto del código
sigue consumiendo ``redis.setex(...)`` etc. sin enterarse del backend.
"""

import logging
import time
from typing import Any, Dict, Optional, Tuple

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[Any] = None
_redis_kind: Optional[str] = None  # "real" | "memory" | None (sin inicializar)


class InMemoryRedis:
    """Mock en memoria de ``redis.asyncio.Redis`` con soporte de TTL.

    Implementa solo los métodos que usa la app. Los valores se guardan con su
    vencimiento (epoch); al leer se descartan los expirados. Alcanza para
    desarrollo local (single event-loop).
    """

    def __init__(self) -> None:
        # key -> (value, expires_at_epoch | None)
        self._store: Dict[str, Tuple[Any, Optional[float]]] = {}

    def _expired(self, expires_at: Optional[float]) -> bool:
        return expires_at is not None and time.time() >= expires_at

    def _purge(self, key: str) -> None:
        entry = self._store.get(key)
        if entry and self._expired(entry[1]):
            self._store.pop(key, None)

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> Optional[Any]:
        self._purge(key)
        entry = self._store.get(key)
        return entry[0] if entry else None

    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        expires_at = (time.time() + ex) if ex else None
        self._store[key] = (value, expires_at)
        return True

    async def setex(self, key: str, ttl_seconds: int, value: Any) -> bool:
        return await self.set(key, value, ex=ttl_seconds)

    async def expire(self, key: str, ttl_seconds: int) -> bool:
        entry = self._store.get(key)
        if entry is None:
            return False
        self._store[key] = (entry[0], time.time() + ttl_seconds)
        return True

    async def delete(self, key: str) -> int:
        removed = self._store.pop(key, None)
        return 1 if removed is not None else 0

    async def exists(self, key: str) -> int:
        self._purge(key)
        return 1 if key in self._store else 0

    async def close(self) -> None:
        self._store.clear()

    async def aclose(self) -> None:
        self._store.clear()


async def _probe_redis(url: str, timeout: float = 1.0) -> bool:
    """Ping no bloqueante para decidir si Redis real está disponible."""
    try:
        client = aioredis.from_url(
            url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=timeout,
            socket_timeout=timeout,
            retry_on_timeout=False,
        )
        try:
            await client.ping()
            return True
        finally:
            await client.aclose()
    except Exception:
        return False


async def get_redis_client() -> Any:
    """Devuelve el cliente Redis global (singleton), lazy y por entorno.

    - **Producción**: cliente Redis real; los errores se propagan al llamador.
      El ping de validación lo hace el lifespan al arranque.
    - **Desarrollo**: intenta Redis real; si no está, cae a ``InMemoryRedis``.

    El resultado se cachea. Reinicializar requiere ``reset_redis_client()``
    (usado en tests).
    """
    global _redis_client, _redis_kind

    if _redis_client is not None:
        return _redis_client

    url = settings.redis_url

    if settings.is_production:
        # En prod Redis es mandatorio: cliente real con timeouts acotados.
        client = aioredis.from_url(
            url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=2.0,
            retry_on_timeout=False,
        )
        _redis_client = client
        _redis_kind = "real"
        return client

    # Desarrollo: probar Redis real primero; si no está, mock en memoria.
    reachable = await _probe_redis(url)
    if reachable:
        client = aioredis.from_url(
            url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=2.0,
            retry_on_timeout=False,
        )
        _redis_client = client
        _redis_kind = "real"
        logger.info("Redis real conectado en desarrollo (%s).", url)
    else:
        _redis_client = InMemoryRedis()
        _redis_kind = "memory"
        logger.warning(
            "Redis no disponible en desarrollo: usando mock en memoria. "
            "Logout/blacklist/reset funcionan pero NO persisten entre reinicios."
        )
    return _redis_client


def reset_redis_client() -> None:
    """Resetea el singleton. Útil para tests que necesitan reconstruir el cliente."""
    global _redis_client, _redis_kind
    _redis_client = None
    _redis_kind = None


def redis_kind() -> Optional[str]:
    """Inspect: devuelve el backend activo ('real' | 'memory' | None)."""
    return _redis_kind


async def close_redis_client() -> None:
    """Cierra el cliente/pool global al apagar la aplicación."""
    global _redis_client, _redis_kind
    if _redis_client is not None:
        try:
            aclose = getattr(_redis_client, "aclose", None) or getattr(
                _redis_client, "close", None
            )
            if aclose is not None:
                await aclose()
        except Exception:
            logger.warning("Error cerrando el cliente Redis global.", exc_info=True)
    _redis_client = None
    _redis_kind = None
