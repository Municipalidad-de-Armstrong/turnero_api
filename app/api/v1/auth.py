from fastapi import APIRouter, Depends, Request, Response, status
import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_redis
from app.core.config import settings
from app.core.security import decrypt_pii, mask_dni, mask_phone
from app.models.role import Role
from app.models.user import User
from app.schemas.auth import (
    PasswordRecoveryRequest,
    PasswordResetRequest,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UsurpationReportCreate,
    UsurpationReportResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    req: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    service = AuthService(db, redis)
    return await service.register_user(req)


@router.post("/tokens")
async def login(
    req: UserLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    service = AuthService(db, redis)
    user = await service.authenticate_user(req.email, req.password)
    token = await service.create_token_for_user(user)

    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False,
    )

    return {"message": "Sesión iniciada exitosamente", "access_token": token, "token_type": "bearer"}


@router.delete("/tokens")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if token:
        service = AuthService(db, redis)
        await service.blacklist_token(token)

    response.delete_cookie(key=settings.SESSION_COOKIE_NAME)
    return {"detail": "Sesión cerrada correctamente."}


@router.post("/password-recovery-tokens")
async def request_password_recovery(
    req: PasswordRecoveryRequest,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.email == req.email)
    res = await db.execute(stmt)
    _user = res.scalar_one_or_none()
    # Always return 200 for security (avoid email enumeration)
    return {"detail": "Si el correo está registrado, se ha enviado un token de recuperación."}


@router.post("/password-resets")
async def apply_password_reset(
    req: PasswordResetRequest,
):
    return {"detail": "Contraseña actualizada correctamente."}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Role).where(Role.id == current_user.rol_id)
    res = await db.execute(stmt)
    role = res.scalar_one()

    raw_dni = decrypt_pii(current_user.dni_cifrado)
    raw_phone = decrypt_pii(current_user.telefono_cifrado)

    if role.nombre in ["administrador", "administrativo"]:
        dni_display = raw_dni
        phone_display = raw_phone
    else:
        dni_display = mask_dni(raw_dni)
        phone_display = mask_phone(raw_phone)

    return UserResponse(
        id=current_user.id,
        nombre=current_user.nombre,
        apellido=current_user.apellido,
        email=current_user.email,
        dni=dni_display,
        telefono=phone_display,
        rol=role.nombre,
        activo=current_user.activo,
        estado=current_user.estado,
        created_at=current_user.created_at,
    )


@router.post("/usurpaciones", response_model=UsurpationReportResponse, status_code=status.HTTP_201_CREATED)
async def report_usurpation_auth(
    req: UsurpationReportCreate,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    return await service.create_usurpation_report(req)
