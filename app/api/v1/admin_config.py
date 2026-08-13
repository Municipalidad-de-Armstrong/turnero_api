from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.models.configuracion_global import ConfiguracionGlobal
from app.schemas.configuracion_global import (
    GlobalConfigResponse,
    GlobalConfigUpdateRequest,
)

router = APIRouter(prefix="/admin/configuracion", tags=["Admin Configuration"])


@router.get(
    "",
    response_model=GlobalConfigResponse,
    dependencies=[Depends(require_roles(["ADMINISTRADOR"]))],
)
async def get_global_config(
    db: AsyncSession = Depends(get_db),
):
    """Obtiene los parámetros de configuración global del sistema (exclusivo ADMINISTRADOR)."""
    stmt = select(ConfiguracionGlobal).where(ConfiguracionGlobal.id == 1)
    res = await db.execute(stmt)
    config = res.scalar_one_or_none()
    if not config:
        config = ConfiguracionGlobal(id=1, anticipacion_cancelacion_horas=24)
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config


@router.patch(
    "",
    response_model=GlobalConfigResponse,
    dependencies=[Depends(require_roles(["ADMINISTRADOR"]))],
)
async def update_global_config(
    req: GlobalConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Actualiza variables de configuración global del sistema (exclusivo ADMINISTRADOR)."""
    stmt = select(ConfiguracionGlobal).where(ConfiguracionGlobal.id == 1)
    res = await db.execute(stmt)
    config = res.scalar_one_or_none()
    if not config:
        config = ConfiguracionGlobal(id=1, anticipacion_cancelacion_horas=24)
        db.add(config)

    if req.anticipacion_cancelacion_horas is not None:
        if req.anticipacion_cancelacion_horas < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El tiempo de anticipación debe ser de al menos 1 hora.",
            )
        config.anticipacion_cancelacion_horas = req.anticipacion_cancelacion_horas

    await db.commit()
    await db.refresh(config)
    return config
