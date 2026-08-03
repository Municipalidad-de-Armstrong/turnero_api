from typing import List, Optional
import secrets
import logging
from fastapi import HTTPException, status
import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import (
    create_access_token,
    decrypt_pii,
    encrypt_pii,
    hash_dni_hmac,
    hash_password,
    mask_dni,
    mask_phone,
    verify_password,
)
from app.models.role import Role
from app.models.user import User
from app.models.usurpation_report import UsurpationReport
from app.schemas.auth import (
    UserRegisterRequest,
    UserResponse,
    UsurpationReportCreate,
    UsurpationReportResponse,
)

logger = logging.getLogger(__name__)

PASSWORD_RESET_KEY_PREFIX = "pwdreset"


class AuthService:
    def __init__(self, db: AsyncSession, redis: Optional[aioredis.Redis] = None):
        self.db = db
        self.redis = redis

    async def register_user(self, req: UserRegisterRequest) -> UserResponse:
        stmt_email = select(User).where(User.email == req.email)
        res_email = await self.db.execute(stmt_email)
        if res_email.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya se encuentra registrado.",
            )

        dni_hmac_val = hash_dni_hmac(req.dni)
        stmt_dni = select(User).where(User.dni_hmac == dni_hmac_val)
        res_dni = await self.db.execute(stmt_dni)
        if res_dni.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El DNI ya se encuentra registrado en el sistema.",
            )

        stmt_role = select(Role).where(Role.nombre == "ciudadano")
        res_role = await self.db.execute(stmt_role)
        role = res_role.scalar_one_or_none()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Configuración del sistema incompleta. Contacte al administrador.",
            )

        user = User(
            nombre=req.nombre,
            apellido=req.apellido,
            email=req.email,
            password_hash=hash_password(req.password),
            dni_cifrado=encrypt_pii(req.dni),
            dni_hmac=dni_hmac_val,
            telefono_cifrado=encrypt_pii(req.telefono),
            rol_id=role.id,
            activo=True,
            estado="ACTIVE",
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return UserResponse(
            id=user.id,
            nombre=user.nombre,
            apellido=user.apellido,
            email=user.email,
            dni=mask_dni(req.dni),
            telefono=mask_phone(req.telefono),
            rol=role.nombre,
            activo=user.activo,
            estado=user.estado,
            created_at=user.created_at,
        )

    async def authenticate_user(self, email: str, password: str) -> User:
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas.",
            )
        if not user.activo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo o suspendido por auditoría.",
            )
        return user

    async def create_token_for_user(self, user: User) -> str:
        stmt = select(Role).where(Role.id == user.rol_id)
        res = await self.db.execute(stmt)
        role = res.scalar_one()

        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": role.nombre,
        }
        return create_access_token(payload)

    async def blacklist_token(self, token: str) -> None:
        """Revoca un JWT guardándolo en la blacklist de Redis con TTL = vida del token.

        En **producción** Redis es obligatorio: si la escritura falla, el error se
        propaga (no tiene sentido un logout silenciosamente fallido). En **dev**
        (con el mock en memoria) los errores se ignoran para no romper flujos.
        """
        if not self.redis:
            # En dev sin Redis esto no debería ocurrir (el mock siempre está),
            # pero por robustez: no romper el logout por esto.
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

    async def create_password_reset_token(self, email: str) -> None:
        """Genera un token opaco de reseteo y lo persiste en Redis con TTL corto.

        Sigue el patrón de la blacklist de JWT (``redis.setex`` con TTL). El envío del
        correo con el enlace queda desacoplado: en DEV se imprime el link en consola
        para permitir probar el flujo E2E; el SMTP real asíncrono se implementa en el
        Slice 10 (notifications) vía Celery.
        """
        if not self.redis:
            # Sin Redis no se puede validar el token. En dev se omite silenciosamente
            # (preserva respuesta anti-enumeración); en prod no debería llegar aquí
            # porque el lifespan exige Redis.
            if settings.is_production:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="El servicio de recuperación de contraseña no está disponible.",
                )
            logger.warning("Redis no disponible en dev: no se emitió token de reseteo.")
            return

        stmt = select(User).where(User.email == email)
        res = await self.db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user or not user.activo or user.estado == "INACTIVE":
            # Usuario inexistente/inactivo: no emitir token (anti-enumeración).
            return

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
            return

        reset_link = (
            f"{settings.APP_BASE_URL.rstrip('/')}/auth/resetear-password?token={token}"
        )
        await self._send_reset_link(email, reset_link)

    async def _send_reset_link(self, email: str, reset_link: str) -> None:
        """Despacha el enlace de reseteo al usuario.

        En DEV se imprime en consola/logs para permitir probar el flujo E2E. El envío
        real por SMTP STARTTLS asíncrono (Celery) se implementa en el Slice 10.
        """
        # TODO(Slice 10): enviar por SMTP STARTTLS/Celery en lugar de log.
        if settings.is_development:
            logger.info("DEV password reset link para %s: %s", email, reset_link)
        else:
            logger.info("Token de reseteo emitido para %s (envío SMTP pendiente).", email)

    async def apply_password_reset(self, token: str, new_password: str) -> None:
        """Valida el token contra Redis, actualiza la contraseña y consume el token
        (single-use). Lanza 400 si el token es inválido/expirado, 503 si Redis cae."""
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
        # Single-use: el token ya no sirve para un nuevo reseteo.
        try:
            await self.redis.delete(key)
        except Exception:
            if settings.is_production:
                # El commit ya se hizo; no revertimos la password por esto, pero
                # dejamos registro para investigar. El token quedó activo (reusable).
                logger.error(
                    "Redis cayó tras aplicar reset de password para user_id=%s. "
                    "El token NO se consumió (queda reusable).", user_id, exc_info=True
                )
            else:
                logger.warning("Redis caído en dev: token de reseteo no consumido.", exc_info=True)

    async def create_usurpation_report(
        self, req: UsurpationReportCreate
    ) -> UsurpationReportResponse:
        dni_hmac_val = hash_dni_hmac(req.dni)
        report = UsurpationReport(
            nombre=req.nombre,
            apellido=req.apellido,
            dni_hmac=dni_hmac_val,
            dni_cifrado=encrypt_pii(req.dni),
            email_contacto=req.email_contacto,
            telefono_cifrado=encrypt_pii(req.telefono),
            motivo=req.motivo,
            estado="PENDIENTE",
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)

        return UsurpationReportResponse(
            id=report.id,
            nombre=report.nombre,
            apellido=report.apellido,
            dni_mascarado=mask_dni(req.dni),
            email_contacto=report.email_contacto,
            telefono_mascarado=mask_phone(req.telefono),
            motivo=report.motivo,
            estado=report.estado,
            created_at=report.created_at,
            resolved_at=report.resolved_at,
        )

    async def list_usurpation_reports(self) -> List[UsurpationReportResponse]:
        stmt = select(UsurpationReport).order_by(UsurpationReport.created_at.desc())
        res = await self.db.execute(stmt)
        reports = res.scalars().all()
        out = []
        for r in reports:
            raw_dni = decrypt_pii(r.dni_cifrado)
            raw_phone = decrypt_pii(r.telefono_cifrado)
            out.append(
                UsurpationReportResponse(
                    id=r.id,
                    nombre=r.nombre,
                    apellido=r.apellido,
                    dni_mascarado=mask_dni(raw_dni),
                    email_contacto=r.email_contacto,
                    telefono_mascarado=mask_phone(raw_phone),
                    motivo=r.motivo,
                    estado=r.estado,
                    created_at=r.created_at,
                    resolved_at=r.resolved_at,
                )
            )
        return out
