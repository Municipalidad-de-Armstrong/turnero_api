
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.schemas.area import AreaCreateRequest, AreaResponse, AreaUpdateRequest
from app.schemas.tramite import TramiteResponse
from app.services.catalog_service import CatalogService

router = APIRouter(tags=["Áreas"])


@router.get("/areas", response_model=list[AreaResponse])
async def list_areas(db: AsyncSession = Depends(get_db)):
    return await CatalogService.get_all_areas(db)


@router.post("/areas", response_model=AreaResponse, status_code=status.HTTP_201_CREATED)
async def create_area(
    req: AreaCreateRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(["administrador", "administrativo"])),
):
    return await CatalogService.create_area(db, req)


@router.patch("/areas/{area_id}", response_model=AreaResponse)
async def update_area(
    area_id: int,
    req: AreaUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(["administrador", "administrativo"])),
):
    return await CatalogService.update_area(db, area_id, req)


@router.delete("/areas/{area_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_area(
    area_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(["administrador", "administrativo"])),
):
    await CatalogService.delete_area(db, area_id)


@router.get("/areas/{area_id}/tramites", response_model=list[TramiteResponse])
async def list_tramites_by_area(area_id: int, db: AsyncSession = Depends(get_db)):
    return await CatalogService.get_tramites_by_area(db, area_id)
