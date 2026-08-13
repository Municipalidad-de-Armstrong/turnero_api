from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.core.security import decrypt_pii, mask_dni, mask_phone
from app.models.usurpation_report import UsurpationReport
from app.schemas.auth import (
    UsurpationReportCreate,
    UsurpationReportResponse,
    UsurpationReportUpdate,
)
from app.services.auth_service import AuthService

router = APIRouter(tags=["Admin Usurpaciones"])


@router.post("/reportes-usurpacion", response_model=UsurpationReportResponse, status_code=status.HTTP_201_CREATED)
async def create_public_report(
    req: UsurpationReportCreate,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    return await service.create_usurpation_report(req)


@router.get("/admin/reportes-usurpacion", response_model=list[UsurpationReportResponse])
@router.get("/admin/usurpaciones", response_model=list[UsurpationReportResponse])
async def list_usurpations(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(["administrador", "administrativo"])),
):
    service = AuthService(db)
    return await service.list_usurpation_reports()


@router.patch("/admin/reportes-usurpacion/{reporte_id}", response_model=UsurpationReportResponse)
@router.patch("/admin/usurpaciones/{reporte_id}", response_model=UsurpationReportResponse)
async def update_usurpation_status(
    reporte_id: int,
    req: UsurpationReportUpdate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(["administrador", "administrativo"])),
):
    stmt = select(UsurpationReport).where(UsurpationReport.id == reporte_id)
    res = await db.execute(stmt)
    report = res.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reporte de usurpación no encontrado.",
        )

    report.estado = req.estado
    if req.estado in ["RESUELTO", "RECHAZADO"]:
        report.resolved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(report)

    raw_dni = decrypt_pii(report.dni_cifrado)
    raw_phone = decrypt_pii(report.telefono_cifrado)

    return UsurpationReportResponse(
        id=report.id,
        nombre=report.nombre,
        apellido=report.apellido,
        dni_mascarado=mask_dni(raw_dni),
        email_contacto=report.email_contacto,
        telefono_mascarado=mask_phone(raw_phone),
        motivo=report.motivo,
        estado=report.estado,
        created_at=report.created_at,
        resolved_at=report.resolved_at,
    )
