from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis_client
from app.core.security import decode_access_token
from app.models.user import User


async def get_redis() -> AsyncGenerator[aioredis.Redis | None, None]:
    """Devuelve el cliente Redis global (real o mock en dev), lazy-inicializado."""
    client = await get_redis_client()
    yield client


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis | None = Depends(get_redis),
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
        except HTTPException:
            raise
        except Exception:
            # En producción Redis es mandatorio: un error aquí debe impedir el
            # acceso (fail-closed) en vez de dejar pasar el token. En dev se
            # tolera (el mock en memoria nunca entra acá).
            if settings.is_production:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Servicio de sesiones no disponible.",
                )

    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub", 0))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
        )

    stmt = select(User).options(selectinload(User.rol)).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo.",
        )

    return user


def require_roles(allowed_roles: list[str]):
    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        allowed_normalized = [r.lower().strip() for r in allowed_roles]
        if current_user.rol.nombre.lower().strip() not in allowed_normalized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permisos insuficientes.",
            )
        return current_user

    return role_checker
