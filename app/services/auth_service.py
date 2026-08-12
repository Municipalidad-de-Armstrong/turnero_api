from typing import List, Optional
import logging
from fastapi import HTTPException, status
import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
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
from app.services.auth_token_service import AuthTokenService, PASSWORD_RESET_KEY_PREFIX

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession, redis: Optional[aioredis.Redis] = None):
        self.db = db
        self.redis = redis
        self._token_service = AuthTokenService(db, redis)

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
            dni=req.dni,
            telefono=req.telefono,
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
        await self._token_service.blacklist_token(token)

    async def is_token_blacklisted(self, token: str) -> bool:
        return await self._token_service.is_token_blacklisted(token)

    async def create_password_reset_token(self, email: str) -> None:
        token = await self._token_service.create_password_reset_token(email)
        if token:
            from app.core.config import settings
            reset_link = (
                f"{settings.APP_BASE_URL.rstrip('/')}/auth/resetear-password?token={token}"
            )
            await self._send_reset_link(email, reset_link)

    async def _send_reset_link(self, email: str, reset_link: str) -> None:
        await self._token_service._send_reset_link(email, reset_link)

    async def apply_password_reset(self, token: str, new_password: str) -> None:
        await self._token_service.apply_password_reset(token, new_password)

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
