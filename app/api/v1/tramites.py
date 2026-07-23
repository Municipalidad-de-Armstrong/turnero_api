from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.schemas.tramite import (
    TramiteCreateRequest,
    TramiteDetailResponse,
    TramiteResponse,
    TramiteUpdateRequest,
)
from app.services.catalog_service import CatalogService

router = APIRouter(tags=["Trámites"])


@router.get("/tramites", response_model=List[TramiteResponse])
async def list_tramites(
    area_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await CatalogService.get_all_tramites(db, area_id=area_id, search=search)


@router.post("/tramites", response_model=TramiteResponse, status_code=status.HTTP_201_CREATED)
async def create_tramite(
    req: TramiteCreateRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(["administrador", "administrativo"])),
):
    return await CatalogService.create_tramite(db, req)


@router.get("/tramites/{tramite_id}", response_model=TramiteDetailResponse)
async def get_tramite_detail(tramite_id: int, db: AsyncSession = Depends(get_db)):
    return await CatalogService.get_tramite_by_id(db, tramite_id)


@router.patch("/tramites/{tramite_id}", response_model=TramiteResponse)
async def update_tramite(
    tramite_id: int,
    req: TramiteUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(["administrador", "administrativo"])),
):
    return await CatalogService.update_tramite(db, tramite_id, req)


@router.delete("/tramites/{tramite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tramite(
    tramite_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(["administrador", "administrativo"])),
):
    await CatalogService.delete_tramite(db, tramite_id)
