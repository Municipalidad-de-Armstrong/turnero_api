from typing import Dict, List, Tuple, Union
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encrypt_pii, hash_dni_hmac, hash_password
from app.models.role import Role
from app.models.user import User

ROLES_DATA: List[Tuple[int, str, str]] = [
    (1, "ciudadano", "Ciudadano solicitante de turnos"),
    (2, "administrativo", "Personal administrativo de atención"),
    (3, "administrador", "Administrador general del sistema"),
]

DEV_ACCOUNTS: List[Dict[str, Union[str, int]]] = [
    {
        "email": "admin.dev@armstrong.gov.ar",
        "password": "Admin123!",
        "nombre": "Admin",
        "apellido": "Desarrollo",
        "dni": "11111111",
        "telefono": "3471000001",
        "rol_id": 3,
    },
    {
        "email": "operador.dev@armstrong.gov.ar",
        "password": "Operador123!",
        "nombre": "Carlos",
        "apellido": "Operador",
        "dni": "22222222",
        "telefono": "3471000002",
        "rol_id": 2,
    },
    {
        "email": "operador2.dev@armstrong.gov.ar",
        "password": "Operador123!",
        "nombre": "Marta",
        "apellido": "Inspectora",
        "dni": "22222223",
        "telefono": "3471000004",
        "rol_id": 2,
    },
    {
        "email": "ciudadano.dev@armstrong.gov.ar",
        "password": "Ciudadano123!",
        "nombre": "Juan",
        "apellido": "Pérez",
        "dni": "33333333",
        "telefono": "3471000003",
        "rol_id": 1,
    },
    {
        "email": "ciudadano2.dev@armstrong.gov.ar",
        "password": "Ciudadano123!",
        "nombre": "María",
        "apellido": "González",
        "dni": "44444444",
        "telefono": "3471000005",
        "rol_id": 1,
    },
    {
        "email": "ciudadano3.dev@armstrong.gov.ar",
        "password": "Ciudadano123!",
        "nombre": "Roberto",
        "apellido": "Fernández",
        "dni": "55555555",
        "telefono": "3471000006",
        "rol_id": 1,
    },
]


async def seed_roles_and_users(session: AsyncSession) -> Dict[str, User]:
    """Seed roles and dev user accounts. Returns dict of users keyed by email."""
    for role_id, role_name, role_desc in ROLES_DATA:
        stmt = select(Role).where(Role.id == role_id)
        res = await session.execute(stmt)
        if not res.scalar_one_or_none():
            session.add(Role(id=role_id, nombre=role_name, descripcion=role_desc))
    await session.commit()

    created_users: Dict[str, User] = {}
    for acc in DEV_ACCOUNTS:
        email = str(acc["email"])
        stmt = select(User).where(User.email == email)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            user = User(
                nombre=str(acc["nombre"]),
                apellido=str(acc["apellido"]),
                email=email,
                password_hash=hash_password(str(acc["password"])),
                dni_cifrado=encrypt_pii(str(acc["dni"])),
                dni_hmac=hash_dni_hmac(str(acc["dni"])),
                telefono_cifrado=encrypt_pii(str(acc["telefono"])),
                rol_id=int(acc["rol_id"]),
                activo=True,
                estado="ACTIVE",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        created_users[email] = user

    return created_users
