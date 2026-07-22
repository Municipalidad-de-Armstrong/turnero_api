from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_roles
from app.core.security import decrypt_pii, encrypt_pii, hash_dni_hmac, mask_dni, mask_phone
from app.models.role import Role
from app.models.user import User
from app.schemas.auth import UserResponse, UserUpdateRequest

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
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


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    req: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.email and req.email != current_user.email:
        stmt = select(User).where(User.email == req.email)
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El correo electrónico ya se encuentra registrado.",
            )
        current_user.email = req.email
        # Modifying email moves account to PENDING_VALIDATION as per HU-04 CA line 31
        current_user.estado = "PENDING_VALIDATION"

    if req.telefono:
        current_user.telefono_cifrado = encrypt_pii(req.telefono)

    await db.commit()
    await db.refresh(current_user)
    return await get_my_profile(current_user, db)


@router.get("", response_model=List[UserResponse])
async def list_usuarios(
    dni: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    rol: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(["administrador", "administrativo"])),
):
    stmt = select(User)
    if email:
        stmt = stmt.where(User.email == email)
    if dni:
        dni_hmac_val = hash_dni_hmac(dni)
        stmt = stmt.where(User.dni_hmac == dni_hmac_val)
    if rol:
        stmt_role = select(Role).where(Role.nombre == rol.lower())
        role_res = await db.execute(stmt_role)
        role_obj = role_res.scalar_one_or_none()
        if role_obj:
            stmt = stmt.where(User.rol_id == role_obj.id)

    res = await db.execute(stmt)
    users = res.scalars().all()

    out = []
    for u in users:
        role_res = await db.execute(select(Role).where(Role.id == u.rol_id))
        role_name = role_res.scalar_one().nombre
        raw_dni = decrypt_pii(u.dni_cifrado)
        raw_phone = decrypt_pii(u.telefono_cifrado)
        out.append(
            UserResponse(
                id=u.id,
                nombre=u.nombre,
                apellido=u.apellido,
                email=u.email,
                dni=raw_dni,
                telefono=raw_phone,
                rol=role_name,
                activo=u.activo,
                estado=u.estado,
                created_at=u.created_at,
            )
        )
    return out
