from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agenda_configuracion import AgendaConfiguracion


async def seed_agenda_configs(
    session: AsyncSession, catalog: dict[str, dict[str, Any]]
) -> None:
    """Seed distinct agenda configurations for each tramite."""
    agenda_rules: dict[str, list[tuple[int, str, str, int]]] = {
        "Licencia de Conducir": [
            (day, "08:00", "12:00", 2) for day in range(1, 6)
        ],
        "Libre Deuda de Infracciones": [
            (day, "07:30", "13:00", 4) for day in range(1, 6)
        ],
        "Permiso de Edificación y Obra": [
            (day, "09:00", "13:00", 1) for day in (1, 3, 5)
        ],
        "Habilitación Comercial e Industrial": [
            (day, "08:30", "12:30", 2) for day in (2, 4)
        ],
    }

    for tr_name, rules in agenda_rules.items():
        if tr_name not in catalog:
            continue
        tramite = catalog[tr_name]["tramite"]
        for dia, hora_ini, hora_fin, capacidad in rules:
            stmt = select(AgendaConfiguracion).where(
                AgendaConfiguracion.tramite_id == tramite.id,
                AgendaConfiguracion.dia_semana == dia,
            )
            res = await session.execute(stmt)
            if not res.scalar_one_or_none():
                agenda = AgendaConfiguracion(
                    tramite_id=tramite.id,
                    dia_semana=dia,
                    hora_inicio=hora_ini,
                    hora_fin=hora_fin,
                    capacidad_simultanea=capacidad,
                    activo=True,
                )
                session.add(agenda)
    await session.commit()
