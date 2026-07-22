from typing import AsyncGenerator, List, Optional
from fastapi import Depends, HTTPException, Request, status
import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.role import Role
from app.models.user import User


async def get_redis() -> AsyncGenerator[Optional[aioredis.Redis], None]:
    client = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    try:
        await client.ping()
        yield client
    except Exception:
        yield None
    finally:
        try:
            await client.aclose()
        except Exception:
            pass


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

    stmt = select(User).where(User.id == user_id)
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
        db: AsyncSession = Depends(get_db),
    ) -> User:
        stmt = select(Role).where(Role.id == current_user.rol_id)
        res = await db.execute(stmt)
        role = res.scalar_one()

        if role.nombre not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permisos insuficientes.",
            )
        return current_user

    return role_checker
