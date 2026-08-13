
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.core.security import (
    decrypt_pii,
    encrypt_pii,
    hash_dni_hmac,
    hash_password,
)
from app.models.role import Role
from app.models.user import User
from app.schemas.admin_user import CreateAdminRequest, UpdateAdminRequest
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/admin/administrativos", tags=["Admin Operadores"])


@router.get(
    "",
    response_model=list[UserResponse],
    dependencies=[Depends(require_roles(["ADMINISTRADOR"]))],
)
async def list_administrativos(
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los usuarios con rol de Administrativo (exclusivo ADMINISTRADOR)."""
    stmt_role = select(Role).where(Role.nombre == "administrativo")
    res_role = await db.execute(stmt_role)
    role_obj = res_role.scalar_one_or_none()
    if not role_obj:
        return []

    stmt = select(User).where(User.rol_id == role_obj.id)
    res = await db.execute(stmt)
    users = res.scalars().all()

    out = []
    for u in users:
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
                rol=role_obj.nombre,
                activo=u.activo,
                estado=u.estado,
                created_at=u.created_at,
            )
        )
    return out


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(["ADMINISTRADOR"]))],
)
async def create_administrativo(
    req: CreateAdminRequest,
    db: AsyncSession = Depends(get_db),
):
    """Crea una nueva cuenta administrativa (exclusivo ADMINISTRADOR)."""
    # Verificar unicidad de email y DNI
    stmt_email = select(User).where(User.email == req.email)
    res_email = await db.execute(stmt_email)
    if res_email.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo electrónico ya se encuentra registrado.",
        )

    dni_hmac_val = hash_dni_hmac(req.dni)
    stmt_dni = select(User).where(User.dni_hmac == dni_hmac_val)
    res_dni = await db.execute(stmt_dni)
    if res_dni.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El DNI ya se encuentra registrado en el sistema.",
        )

    # Obtener rol administrativo (id=2)
    stmt_role = select(Role).where(Role.nombre == "administrativo")
    res_role = await db.execute(stmt_role)
    role_obj = res_role.scalar_one_or_none()
    if not role_obj:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Rol administrativo no configurado en la base de datos.",
        )

    new_user = User(
        nombre=req.nombre,
        apellido=req.apellido,
        email=req.email,
        password_hash=hash_password(req.password),
        dni_cifrado=encrypt_pii(req.dni),
        dni_hmac=dni_hmac_val,
        telefono_cifrado=encrypt_pii(req.telefono),
        rol_id=role_obj.id,
        activo=True,
        estado="ACTIVE",
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return UserResponse(
        id=new_user.id,
        nombre=new_user.nombre,
        apellido=new_user.apellido,
        email=new_user.email,
        dni=req.dni,
        telefono=req.telefono,
        rol=role_obj.nombre,
        activo=new_user.activo,
        estado=new_user.estado,
        created_at=new_user.created_at,
    )


@router.patch(
    "/{id}",
    response_model=UserResponse,
    dependencies=[Depends(require_roles(["ADMINISTRADOR"]))],
)
async def update_administrativo(
    id: int,
    req: UpdateAdminRequest,
    db: AsyncSession = Depends(get_db),
):
    """Modifica los datos de una cuenta administrativa (exclusivo ADMINISTRADOR)."""
    stmt = select(User).where(User.id == id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario administrativo no encontrado.",
        )

    if req.email and req.email != user.email:
        stmt_e = select(User).where(User.email == req.email)
        res_e = await db.execute(stmt_e)
        if res_e.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El correo electrónico ya se encuentra en uso.",
            )
        user.email = req.email

    if req.nombre:
        user.nombre = req.nombre
    if req.apellido:
        user.apellido = req.apellido
    if req.telefono:
        user.telefono_cifrado = encrypt_pii(req.telefono)
    if req.password:
        user.password_hash = hash_password(req.password)
    if req.activo is not None:
        user.activo = req.activo
        user.estado = "ACTIVE" if req.activo else "INACTIVE"

    await db.commit()
    await db.refresh(user)

    role_res = await db.execute(select(Role).where(Role.id == user.rol_id))
    role_name = role_res.scalar_one().nombre

    return UserResponse(
        id=user.id,
        nombre=user.nombre,
        apellido=user.apellido,
        email=user.email,
        dni=decrypt_pii(user.dni_cifrado),
        telefono=decrypt_pii(user.telefono_cifrado),
        rol=role_name,
        activo=user.activo,
        estado=user.estado,
        created_at=user.created_at,
    )


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(["ADMINISTRADOR"]))],
)
async def delete_administrativo(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Elimina / deshabilita una cuenta administrativa (exclusivo ADMINISTRADOR)."""
    stmt = select(User).where(User.id == id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario administrativo no encontrado.",
        )

    # Baja lógica: cambiar a inactivo
    user.activo = False
    user.estado = "INACTIVE"
    await db.commit()
