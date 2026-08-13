from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.configuracion_global import ConfiguracionGlobal


async def seed_global_config(session: AsyncSession) -> ConfiguracionGlobal:
    """Asegura la presencia del registro inicial de ConfiguracionGlobal (id=1)."""
    stmt = select(ConfiguracionGlobal).where(ConfiguracionGlobal.id == 1)
    res = await session.execute(stmt)
    config = res.scalar_one_or_none()
    if not config:
        config = ConfiguracionGlobal(id=1, anticipacion_cancelacion_horas=24)
        session.add(config)
        await session.commit()
        await session.refresh(config)
    return config
