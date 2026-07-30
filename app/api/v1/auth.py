from fastapi import APIRouter, Depends, Request, Response, status
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_redis
from app.core.config import settings
from app.schemas.auth import (
    PasswordRecoveryRequest,
    PasswordResetRequest,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
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
        samesite=settings.SESSION_COOKIE_SAMESITE,
        secure=settings.SESSION_COOKIE_SECURE,
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

    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        secure=settings.SESSION_COOKIE_SECURE,
    )
    return {"detail": "Sesión cerrada correctamente."}


@router.post("/password-recovery-tokens")
async def request_password_recovery(
    req: PasswordRecoveryRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    service = AuthService(db, redis)
    await service.create_password_reset_token(req.email)
    # Always return 200 for security (avoid email enumeration)
    return {"detail": "Si el correo está registrado, se ha enviado un token de recuperación."}


@router.post("/password-resets")
async def apply_password_reset(
    req: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    service = AuthService(db, redis)
    await service.apply_password_reset(req.token, req.new_password)
    return {"detail": "Contraseña actualizada correctamente."}
