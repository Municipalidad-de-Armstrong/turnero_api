import logging
import os
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.uploads import fs_path_to_url, url_to_fs_path
from app.models.tramite import Tramite
from app.models.tramite_documento import TramiteDocumento
from app.models.tramite_enlace import TramiteEnlace
from app.models.variante import Variante
from app.schemas.tramite_enlace import TramiteEnlaceCreateRequest
from app.schemas.variante import VarianteCreateRequest, VarianteUpdateRequest

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
# Subdirectorio dentro de UPLOAD_DIR donde se guardan los formularios de trámites.
TRAMITES_UPLOAD_SUBDIR = "tramites"
UPLOADS_DIR = os.path.join(settings.UPLOAD_DIR, TRAMITES_UPLOAD_SUBDIR)


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
        count_res = await db.execute(
            select(func.count()).where(Variante.tramite_id == variante.tramite_id)
        )
        count = count_res.scalar() or 0
        if count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede eliminar la única variante del trámite. Cada trámite debe conservar al menos una variante.",
            )

        await db.delete(variante)
        await db.commit()

    # --- DOCUMENTOS ADJUNTOS ---
    @staticmethod
    async def get_documentos_by_tramite(
        db: AsyncSession, tramite_id: int
    ) -> list[TramiteDocumento]:
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

        if ext == ".pdf" and not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El contenido del archivo no coincide con la firma binaria de un documento PDF.",
            )
        if ext == ".docx" and not content.startswith(b"PK\x03\x04"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El contenido del archivo no coincide con la firma binaria de un documento DOCX.",
            )
        if ext == ".doc" and not content.startswith(b"\xd0\xcf\x11\xe0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El contenido del archivo no coincide con la firma binaria de un documento DOC.",
            )

        os.makedirs(UPLOADS_DIR, exist_ok=True)
        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(UPLOADS_DIR, unique_name)

        with open(file_path, "wb") as f:
            f.write(content)

        public_url = fs_path_to_url(file_path)
        doc = TramiteDocumento(
            tramite_id=tramite_id, nombre=nombre, ruta_archivo=public_url
        )
        db.add(doc)
        try:
            await db.commit()
        except Exception:
            try:
                os.remove(file_path)
            except OSError:
                logger.warning("No se pudo borrar el archivo huérfano: %s", file_path)
            raise
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
        fs_path = url_to_fs_path(doc.ruta_archivo)
        await db.delete(doc)
        await db.commit()
        if fs_path:
            try:
                os.remove(fs_path)
            except OSError:
                logger.warning("No se pudo borrar el archivo en disco: %s", fs_path)

    # --- ENLACES ÚTILES ---
    @staticmethod
    async def get_enlaces_by_tramite(
        db: AsyncSession, tramite_id: int
    ) -> list[TramiteEnlace]:
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
