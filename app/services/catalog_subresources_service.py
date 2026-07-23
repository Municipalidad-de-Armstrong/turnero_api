import os
import uuid
from typing import List
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tramite import Tramite
from app.models.tramite_documento import TramiteDocumento
from app.models.tramite_enlace import TramiteEnlace
from app.models.variante import Variante
from app.schemas.tramite_enlace import TramiteEnlaceCreateRequest
from app.schemas.variante import VarianteCreateRequest, VarianteUpdateRequest

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
UPLOADS_DIR = os.path.join("uploads", "tramites")


class CatalogSubresourcesService:
    # --- VARIANTES ---
    @staticmethod
    async def create_variante(
        db: AsyncSession, tramite_id: int, data: VarianteCreateRequest
    ) -> Variante:
        tramite_res = await db.execute(select(Tramite).where(Tramite.id == tramite_id))
        if not tramite_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trámite con id {tramite_id} no encontrado",
            )
        variante = Variante(
            tramite_id=tramite_id,
            nombre=data.nombre,
            descripcion=data.descripcion,
            duracion_minutos=data.duracion_minutos,
        )
        db.add(variante)
        await db.commit()
        await db.refresh(variante)
        return variante

    @staticmethod
    async def update_variante(
        db: AsyncSession, variante_id: int, data: VarianteUpdateRequest
    ) -> Variante:
        res = await db.execute(select(Variante).where(Variante.id == variante_id))
        variante = res.scalar_one_or_none()
        if not variante:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Variante con id {variante_id} no encontrada",
            )
        if data.nombre is not None:
            variante.nombre = data.nombre
        if data.descripcion is not None:
            variante.descripcion = data.descripcion
        if data.duracion_minutos is not None:
            variante.duracion_minutos = data.duracion_minutos
        await db.commit()
        await db.refresh(variante)
        return variante

    @staticmethod
    async def delete_variante(db: AsyncSession, variante_id: int) -> None:
        res = await db.execute(select(Variante).where(Variante.id == variante_id))
        variante = res.scalar_one_or_none()
        if not variante:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Variante con id {variante_id} no encontrada",
            )
        await db.delete(variante)
        await db.commit()

    # --- DOCUMENTOS ADJUNTOS ---
    @staticmethod
    async def get_documentos_by_tramite(
        db: AsyncSession, tramite_id: int
    ) -> List[TramiteDocumento]:
        res = await db.execute(
            select(TramiteDocumento)
            .where(TramiteDocumento.tramite_id == tramite_id)
            .order_by(TramiteDocumento.created_at)
        )
        return list(res.scalars().all())

    @staticmethod
    async def upload_documento(
        db: AsyncSession, tramite_id: int, nombre: str, archivo: UploadFile
    ) -> TramiteDocumento:
        tramite_res = await db.execute(select(Tramite).where(Tramite.id == tramite_id))
        if not tramite_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trámite con id {tramite_id} no encontrado",
            )

        filename = archivo.filename or ""
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de archivo no permitido '{ext}'. Permitidos: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        content = await archivo.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo excede el tamaño máximo permitido de 10 MB.",
            )

        os.makedirs(UPLOADS_DIR, exist_ok=True)
        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(UPLOADS_DIR, unique_name)

        with open(file_path, "wb") as f:
            f.write(content)

        relative_path = f"/static/uploads/tramites/{unique_name}"
        doc = TramiteDocumento(
            tramite_id=tramite_id, nombre=nombre, ruta_archivo=relative_path
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        return doc

    @staticmethod
    async def delete_documento(
        db: AsyncSession, tramite_id: int, documento_id: int
    ) -> None:
        res = await db.execute(
            select(TramiteDocumento).where(
                TramiteDocumento.id == documento_id,
                TramiteDocumento.tramite_id == tramite_id,
            )
        )
        doc = res.scalar_one_or_none()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento con id {documento_id} no encontrado para el trámite {tramite_id}",
            )
        await db.delete(doc)
        await db.commit()

    # --- ENLACES ÚTILES ---
    @staticmethod
    async def get_enlaces_by_tramite(
        db: AsyncSession, tramite_id: int
    ) -> List[TramiteEnlace]:
        res = await db.execute(
            select(TramiteEnlace)
            .where(TramiteEnlace.tramite_id == tramite_id)
            .order_by(TramiteEnlace.created_at)
        )
        return list(res.scalars().all())

    @staticmethod
    async def create_enlace(
        db: AsyncSession, tramite_id: int, data: TramiteEnlaceCreateRequest
    ) -> TramiteEnlace:
        tramite_res = await db.execute(select(Tramite).where(Tramite.id == tramite_id))
        if not tramite_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trámite con id {tramite_id} no encontrado",
            )
        enlace = TramiteEnlace(
            tramite_id=tramite_id, descripcion=data.descripcion, url=data.url
        )
        db.add(enlace)
        await db.commit()
        await db.refresh(enlace)
        return enlace

    @staticmethod
    async def delete_enlace(
        db: AsyncSession, tramite_id: int, enlace_id: int
    ) -> None:
        res = await db.execute(
            select(TramiteEnlace).where(
                TramiteEnlace.id == enlace_id,
                TramiteEnlace.tramite_id == tramite_id,
            )
        )
        enlace = res.scalar_one_or_none()
        if not enlace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Enlace con id {enlace_id} no encontrado para el trámite {tramite_id}",
            )
        await db.delete(enlace)
        await db.commit()
