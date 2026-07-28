from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.seeds.agenda_seed import seed_agenda_configs
from app.core.seeds.catalog_seed import seed_catalog
from app.core.seeds.turnos_seed import seed_turnos_and_reports
from app.core.seeds.users_seed import seed_roles_and_users


async def seed_initial_data(session: AsyncSession) -> None:
    """Seed base roles and, if in development mode, seed test accounts, areas,

    tramites, agendas, turnos and usurpation reports.
    """
    users = await seed_roles_and_users(session)

    if settings.ENVIRONMENT.lower() == "development":
        catalog = await seed_catalog(session)
        await seed_agenda_configs(session, catalog)
        await seed_turnos_and_reports(session, users, catalog)
