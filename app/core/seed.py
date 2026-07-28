from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import encrypt_pii, hash_dni_hmac, hash_password
from app.models.agenda_configuracion import AgendaConfiguracion
from app.models.area import Area
from app.models.role import Role
from app.models.tramite import Tramite
from app.models.user import User
from app.models.variante import Variante


async def seed_initial_data(session: AsyncSession) -> None:
    """Seed base roles and, if in development mode, seed test accounts, areas, tramites and agenda."""
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

        # Seed test Area
        stmt_area = select(Area).where(Area.nombre == "Tránsito y Licencias")
        res_area = await session.execute(stmt_area)
        area = res_area.scalar_one_or_none()
        if not area:
            area = Area(
                nombre="Tránsito y Licencias",
                descripcion="Licencias de conducir, exámenes y patentes automotrices.",
            )
            session.add(area)
            await session.commit()
            await session.refresh(area)

        # Seed test Tramite
        stmt_tramite = select(Tramite).where(
            Tramite.nombre == "Licencia de Conducir", Tramite.area_id == area.id
        )
        res_tramite = await session.execute(stmt_tramite)
        tramite = res_tramite.scalar_one_or_none()
        if not tramite:
            tramite = Tramite(
                area_id=area.id,
                nombre="Licencia de Conducir",
                descripcion="Gestión presencial de emisión y renovación de licencias de conducir.",
                documentacion_requerida="**DNI Original** y fotocopia de ambas caras.\n- Certificado de Grupo Sanguíneo firmado por profesional.\n- Ficha médica de aptitud completada.",
                requerimientos_previos="Constatar libre deuda de infracciones de tránsito en el Juzgado de Faltas previo a la cita.",
                emite_carnet=True,
                limite_sobreturnos_diarios=5,
            )
            session.add(tramite)
            await session.commit()
            await session.refresh(tramite)

            # Seed Variantes for Tramite
            var1 = Variante(
                tramite_id=tramite.id,
                nombre="Examen Médico / Psicofísico",
                descripcion="Evaluación de aptitud visual, auditiva y médica.",
                duracion_minutos=15,
            )
            var2 = Variante(
                tramite_id=tramite.id,
                nombre="Examen Teórico de Conducción",
                descripcion="Examen en aula sobre normas de tránsito y señales.",
                duracion_minutos=30,
            )
            session.add_all([var1, var2])
            await session.commit()

        # Seed AgendaConfiguracion for Tramite (Lunes a Viernes de 08:00 a 12:00)
        for day in range(1, 6):  # 1=Lunes, ..., 5=Viernes
            stmt_agenda = select(AgendaConfiguracion).where(
                AgendaConfiguracion.tramite_id == tramite.id,
                AgendaConfiguracion.dia_semana == day,
            )
            res_agenda = await session.execute(stmt_agenda)
            if not res_agenda.scalar_one_or_none():
                agenda = AgendaConfiguracion(
                    tramite_id=tramite.id,
                    dia_semana=day,
                    hora_inicio="08:00",
                    hora_fin="12:00",
                    capacidad_simultanea=2,
                    activo=True,
                )
                session.add(agenda)
        await session.commit()
