from typing import AsyncGenerator, List, Optional
from fastapi import Depends, HTTPException, Request, status
import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis_client
from app.core.security import decode_access_token
from app.models.user import User


async def get_redis() -> AsyncGenerator[Optional[aioredis.Redis], None]:
    """Devuelve el cliente Redis compartido (no lo cierra: se reutiliza entre
    peticiones). Si Redis no está disponible, devuelve ``None`` para que los
    consumidores degraden con elegancia (mismas semántica que antes)."""
    client = get_redis_client()
    try:
        # Ping liviano: valida que el pool tenga una conexión sana. Reusa la misma
        # conexión del pool en lugar de abrir/cerrar una por petición.
        await client.ping()
        yield client
    except Exception:
        yield None


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Optional[aioredis.Redis] = Depends(get_redis),
) -> User:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado.",
        )

    if redis:
        try:
            is_blacklisted = await redis.exists(f"blacklist:{token}")
            if is_blacklisted:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Sesión revocada.",
                )
        except Exception:
            pass

    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub", 0))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
        )

    # Eager-load del rol para evitar una segunda query en /usuarios/me y
    # require_roles (que solo leen current_user.rol.nombre).
    stmt = select(User).options(selectinload(User.rol)).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo.",
        )

    return user


def require_roles(allowed_roles: List[str]):
    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        # El rol ya viene cargado por get_current_user (eager-load), así que no
        # hace falta una segunda query a la base de datos.
        allowed_normalized = [r.lower().strip() for r in allowed_roles]
        if current_user.rol.nombre.lower().strip() not in allowed_normalized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permisos insuficientes.",
            )
        return current_user

    return role_checker
