from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import encrypt_pii, hash_dni_hmac, hash_password
from app.models.role import Role
from app.models.user import User


async def seed_initial_data(session: AsyncSession) -> None:
    """Seed base roles and, if in development mode, seed test accounts for each role."""
    roles_data = [
        (1, "ciudadano", "Ciudadano solicitante de turnos"),
        (2, "administrativo", "Personal administrativo de atención"),
        (3, "administrador", "Administrador general del sistema"),
    ]
    for role_id, role_name, role_desc in roles_data:
        stmt = select(Role).where(Role.id == role_id)
        res = await session.execute(stmt)
        if not res.scalar_one_or_none():
            session.add(Role(id=role_id, nombre=role_name, descripcion=role_desc))
    await session.commit()

    if settings.ENVIRONMENT.lower() == "development":
        dev_accounts = [
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
                "nombre": "Operador",
                "apellido": "Desarrollo",
                "dni": "22222222",
                "telefono": "3471000002",
                "rol_id": 2,
            },
            {
                "email": "ciudadano.dev@armstrong.gov.ar",
                "password": "Ciudadano123!",
                "nombre": "Ciudadano",
                "apellido": "Desarrollo",
                "dni": "33333333",
                "telefono": "3471000003",
                "rol_id": 1,
            },
        ]

        for acc in dev_accounts:
            stmt = select(User).where(User.email == acc["email"])
            res = await session.execute(stmt)
            if not res.scalar_one_or_none():
                user = User(
                    nombre=acc["nombre"],
                    apellido=acc["apellido"],
                    email=acc["email"],
                    password_hash=hash_password(acc["password"]),
                    dni_cifrado=encrypt_pii(acc["dni"]),
                    dni_hmac=hash_dni_hmac(acc["dni"]),
                    telefono_cifrado=encrypt_pii(acc["telefono"]),
                    rol_id=acc["rol_id"],
                    activo=True,
                    estado="ACTIVE",
                )
                session.add(user)
        await session.commit()
