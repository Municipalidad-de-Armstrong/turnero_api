import logging
import secrets

import redis.asyncio as aioredis
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User

logger = logging.getLogger(__name__)

PASSWORD_RESET_KEY_PREFIX = "pwdreset"


class AuthTokenService:
    def __init__(self, db: AsyncSession, redis: aioredis.Redis | None = None):
        self.db = db
        self.redis = redis

    async def blacklist_token(self, token: str) -> None:
        """Revoca un JWT guardándolo en la blacklist de Redis con TTL = vida del token."""
        if not self.redis:
            if settings.is_production:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Servicio de sesiones no disponible.",
                )
            return

        ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        try:
            await self.redis.setex(f"blacklist:{token}", ttl, "true")
        except Exception:
            if settings.is_production:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Servicio de sesiones no disponible.",
                )
            logger.warning("Redis caído en dev: blacklist_token ignorado.", exc_info=True)

    async def is_token_blacklisted(self, token: str) -> bool:
        """Dice si un token fue revocado. En prod propaga errores de Redis."""
        if not self.redis:
            if settings.is_production:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Servicio de sesiones no disponible.",
                )
            return False

        try:
            exists = await self.redis.exists(f"blacklist:{token}")
            return bool(exists)
        except Exception:
            if settings.is_production:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Servicio de sesiones no disponible.",
                )
            logger.warning("Redis caído en dev: is_token_blacklisted -> False.", exc_info=True)
            return False

    async def create_password_reset_token(self, email: str) -> str | None:
        """Genera un token opaco de reseteo y lo persiste en Redis con TTL corto."""
        if not self.redis:
            if settings.is_production:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="El servicio de recuperación de contraseña no está disponible.",
                )
            logger.warning("Redis no disponible en dev: no se emitió token de reseteo.")
            return None

        stmt = select(User).where(User.email == email)
        res = await self.db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user or not user.activo or user.estado == "INACTIVE":
            return None

        token = secrets.token_urlsafe(32)
        ttl = settings.PASSWORD_RESET_TOKEN_TTL_MINUTES * 60
        try:
            await self.redis.setex(
                f"{PASSWORD_RESET_KEY_PREFIX}:{token}", ttl, str(user.id)
            )
        except Exception:
            if settings.is_production:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="El servicio de recuperación de contraseña no está disponible.",
                )
            logger.warning("Redis caído en dev: no se emitió token de reseteo.", exc_info=True)
            return None

        return token

    async def _send_reset_link(self, email: str, reset_link: str) -> None:
        if settings.is_development:
            logger.info("DEV password reset link para %s: %s", email, reset_link)
        else:
            logger.info("Token de reseteo emitido para %s (envío SMTP pendiente).", email)

    async def apply_password_reset(self, token: str, new_password: str) -> None:
        """Valida el token contra Redis, actualiza la contraseña y consume el token."""
        if not self.redis:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="El servicio de recuperación de contraseña no está disponible.",
            )

        key = f"{PASSWORD_RESET_KEY_PREFIX}:{token}"
        try:
            user_id_raw = await self.redis.get(key)
        except Exception:
            if settings.is_production:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="El servicio de recuperación de contraseña no está disponible.",
                )
            logger.warning("Redis caído en dev: apply_password_reset -> 503.", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="El servicio de recuperación de contraseña no está disponible.",
            )
        if not user_id_raw:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token inválido o expirado.",
            )

        try:
            user_id = int(user_id_raw)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token inválido o expirado.",
            )

        stmt = select(User).where(User.id == user_id)
        res = await self.db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token inválido o expirado.",
            )

        user.password_hash = hash_password(new_password)
        await self.db.commit()
        try:
            await self.redis.delete(key)
        except Exception:
            if settings.is_production:
                logger.error(
                    "Redis cayó tras aplicar reset de password para user_id=%s. "
                    "El token NO se consumió (queda reusable).", user_id, exc_info=True
                )
            else:
                logger.warning("Redis caído en dev: token de reseteo no consumido.", exc_info=True)
