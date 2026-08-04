from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.schemas.availability import BloqueDisponibilidad
from app.schemas.tramite import (
    TramiteCreateRequest,
    TramiteDetailResponse,
    TramiteResponse,
    TramiteUpdateRequest,
)
from app.schemas.tramite_documento import TramiteDocumentoResponse
from app.schemas.tramite_enlace import (
    TramiteEnlaceCreateRequest,
    TramiteEnlaceResponse,
)
from app.schemas.variante import (
    VarianteCreateRequest,
    VarianteResponse,
    VarianteUpdateRequest,
)
from app.services.availability_service import AvailabilityService
from app.services.catalog_service import CatalogService
from app.services.catalog_subresources_service import CatalogSubresourcesService

router = APIRouter(tags=["Trámites"])



# --- TRÁMITES ---
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


# --- VARIANTES ---
@router.post(
    "/tramites/{tramite_id}/variantes",
    response_model=VarianteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_variante(
    tramite_id: int,
    req: VarianteCreateRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(["administrador", "administrativo"])),
):
    return await CatalogSubresourcesService.create_variante(db, tramite_id, req)


@router.patch("/variantes/{variante_id}", response_model=VarianteResponse)
async def update_variante(
    variante_id: int,
    req: VarianteUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(["administrador", "administrativo"])),
):
    return await CatalogSubresourcesService.update_variante(db, variante_id, req)


@router.delete("/variantes/{variante_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_variante(
    variante_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(["administrador", "administrativo"])),
):
    await CatalogSubresourcesService.delete_variante(db, variante_id)


# --- DOCUMENTOS ADJUNTOS ---
@router.get(
    "/tramites/{tramite_id}/documentos",
    response_model=List[TramiteDocumentoResponse],
)
async def list_tramite_documentos(
    tramite_id: int, db: AsyncSession = Depends(get_db)
):
    return await CatalogSubresourcesService.get_documentos_by_tramite(db, tramite_id)


@router.post(
    "/tramites/{tramite_id}/documentos",
    response_model=TramiteDocumentoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_tramite_documento(
    tramite_id: int,
    nombre: str = Form(...),
    archivo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(["administrador", "administrativo"])),
):
    return await CatalogSubresourcesService.upload_documento(
        db, tramite_id, nombre, archivo
    )


@router.delete(
    "/tramites/{tramite_id}/documentos/{documento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_tramite_documento(
    tramite_id: int,
    documento_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(["administrador", "administrativo"])),
):
    await CatalogSubresourcesService.delete_documento(db, tramite_id, documento_id)


# --- ENLACES ÚTILES ---
@router.get(
    "/tramites/{tramite_id}/enlaces",
    response_model=List[TramiteEnlaceResponse],
)
async def list_tramite_enlaces(
    tramite_id: int, db: AsyncSession = Depends(get_db)
):
    return await CatalogSubresourcesService.get_enlaces_by_tramite(db, tramite_id)


@router.post(
    "/tramites/{tramite_id}/enlaces",
    response_model=TramiteEnlaceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tramite_enlace(
    tramite_id: int,
    req: TramiteEnlaceCreateRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(["administrador", "administrativo"])),
):
    return await CatalogSubresourcesService.create_enlace(db, tramite_id, req)


@router.delete(
    "/tramites/{tramite_id}/enlaces/{enlace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_tramite_enlace(
    tramite_id: int,
    enlace_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(["administrador", "administrativo"])),
):
    await CatalogSubresourcesService.delete_enlace(db, tramite_id, enlace_id)


# --- DISPONIBILIDAD Y PRIMER TURNO ---
@router.get(
    "/tramites/{tramite_id}/disponibilidad",
    response_model=List[BloqueDisponibilidad],
)
async def get_disponibilidad(
    tramite_id: int,
    fecha: date = Query(...),
    variante_ids: List[int] = Query(default=[]),
    db: AsyncSession = Depends(get_db),
):
    return await AvailabilityService.get_disponibilidad(
        db, tramite_id, fecha, variante_ids
    )


@router.get(
    "/tramites/{tramite_id}/primer-turno-disponible",
    response_model=BloqueDisponibilidad,
)
async def get_primer_turno_disponible(
    tramite_id: int,
    variante_ids: List[int] = Query(default=[]),
    db: AsyncSession = Depends(get_db),
):
    return await AvailabilityService.get_primer_turno_disponible(
        db, tramite_id, variante_ids
    )

