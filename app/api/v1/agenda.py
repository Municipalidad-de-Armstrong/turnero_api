from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.schemas.agenda import AgendaConfigResponse, AgendaConfigSaveItem
from app.services.agenda_service import AgendaService

router = APIRouter(tags=["Trámites"])


@router.get(
    "/tramites/{tramite_id}/agenda-configuracion",
    response_model=List[AgendaConfigResponse],
)
async def get_agenda_configuracion(
    tramite_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(["ciudadano", "administrativo", "administrador"])),
):
    return await AgendaService.get_agenda_config(db, tramite_id)


@router.post(
    "/tramites/{tramite_id}/agenda-configuracion",
    response_model=List[AgendaConfigResponse],
)
async def save_agenda_configuracion(
    tramite_id: int,
    req: List[AgendaConfigSaveItem],
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(["administrador", "administrativo"])),
):
    return await AgendaService.save_agenda_config(db, tramite_id, req)
