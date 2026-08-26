
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.area import Area
from app.models.tramite import Tramite
from app.models.turno import Turno
from app.models.variante import Variante
from app.schemas.area import AreaCreateRequest, AreaUpdateRequest
from app.schemas.tramite import TramiteCreateRequest, TramiteUpdateRequest


class CatalogService:

    @staticmethod
    async def get_all_areas(db: AsyncSession) -> list[Area]:
        result = await db.execute(select(Area).order_by(Area.nombre))
        return list(result.scalars().all())

    @staticmethod
    async def get_area_by_id(db: AsyncSession, area_id: int) -> Area:
        result = await db.execute(select(Area).where(Area.id == area_id))
        area = result.scalar_one_or_none()
        if not area:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Área con id {area_id} no encontrada",
            )
        return area

    @staticmethod
    async def create_area(db: AsyncSession, data: AreaCreateRequest) -> Area:
        clean_name = data.nombre.strip()
        existing = await db.execute(
            select(Area).where(func.lower(Area.nombre) == clean_name.lower())
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un área registrada con el nombre '{clean_name}'",
            )
        area = Area(
            nombre=clean_name,
            descripcion=data.descripcion,
            direccion=data.direccion,
        )
        db.add(area)
        await db.commit()
        await db.refresh(area)
        return area

    @staticmethod
    async def update_area(db: AsyncSession, area_id: int, data: AreaUpdateRequest) -> Area:
        area = await CatalogService.get_area_by_id(db, area_id)
        if data.nombre is not None:
            clean_name = data.nombre.strip()
            if clean_name.lower() != area.nombre.lower():
                existing = await db.execute(
                    select(Area).where(
                        func.lower(Area.nombre) == clean_name.lower(),
                        Area.id != area_id,
                    )
                )
                if existing.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Ya existe otra área con el nombre '{clean_name}'",
                    )
            area.nombre = clean_name
        if data.descripcion is not None:
            area.descripcion = data.descripcion
        if data.direccion is not None:
            area.direccion = data.direccion
        await db.commit()
        await db.refresh(area)
        return area

    @staticmethod
    async def delete_area(db: AsyncSession, area_id: int) -> None:
        area = await CatalogService.get_area_by_id(db, area_id)
        tramites_result = await db.execute(
            select(Tramite).where(Tramite.area_id == area_id)
        )
        if tramites_result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"No se puede eliminar el área '{area.nombre}' porque contiene trámites asociados.",
            )
        await db.delete(area)
        await db.commit()

    @staticmethod
    async def get_all_tramites(
        db: AsyncSession,
        area_id: int | None = None,
        search: str | None = None,
    ) -> list[Tramite]:
        query = (
            select(Tramite)
            .options(
                selectinload(Tramite.area),
                selectinload(Tramite.variantes),
                selectinload(Tramite.documentos),
                selectinload(Tramite.enlaces),
            )
            .order_by(Tramite.nombre)
        )
        if area_id is not None:
            query = query.where(Tramite.area_id == area_id)
        if search:
            query = query.where(Tramite.nombre.ilike(f"%{search}%"))
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_tramites_by_area(db: AsyncSession, area_id: int) -> list[Tramite]:
        await CatalogService.get_area_by_id(db, area_id)
        return await CatalogService.get_all_tramites(db, area_id=area_id)

    @staticmethod
    async def get_tramite_by_id(db: AsyncSession, tramite_id: int) -> Tramite:
        query = (
            select(Tramite)
            .options(
                selectinload(Tramite.area),
                selectinload(Tramite.variantes),
                selectinload(Tramite.documentos),
                selectinload(Tramite.enlaces),
            )
            .where(Tramite.id == tramite_id)
        )
        result = await db.execute(query)
        tramite = result.scalar_one_or_none()
        if not tramite:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trámite con id {tramite_id} no encontrado",
            )
        return tramite


    @staticmethod
    async def create_tramite(db: AsyncSession, data: TramiteCreateRequest) -> Tramite:
        await CatalogService.get_area_by_id(db, data.area_id)
        clean_name = data.nombre.strip()
        existing = await db.execute(
            select(Tramite).where(
                Tramite.area_id == data.area_id,
                func.lower(Tramite.nombre) == clean_name.lower(),
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un trámite registrado con el nombre '{clean_name}' en esta área.",
            )
        tramite = Tramite(
            area_id=data.area_id,
            nombre=clean_name,
            descripcion=data.descripcion.strip() if data.descripcion else None,
            documentacion_requerida=data.documentacion_requerida.strip(),
            requerimientos_previos=data.requerimientos_previos.strip() if data.requerimientos_previos else None,
            emite_carnet=data.emite_carnet,
            limite_sobreturnos_diarios=data.limite_sobreturnos_diarios,
        )
        db.add(tramite)
        await db.flush()

        variante_defecto = Variante(
            tramite_id=tramite.id,
            nombre="Atención General",
            descripcion="Atención estándar del trámite",
            duracion_minutos=15,
        )
        db.add(variante_defecto)
        await db.commit()
        await db.refresh(tramite)
        return tramite

    @staticmethod
    async def update_tramite(
        db: AsyncSession, tramite_id: int, data: TramiteUpdateRequest
    ) -> Tramite:
        tramite = await CatalogService.get_tramite_by_id(db, tramite_id)
        if data.nombre is not None:
            clean_name = data.nombre.strip()
            if clean_name.lower() != tramite.nombre.lower():
                existing = await db.execute(
                    select(Tramite).where(
                        Tramite.area_id == tramite.area_id,
                        func.lower(Tramite.nombre) == clean_name.lower(),
                        Tramite.id != tramite_id,
                    )
                )
                if existing.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Ya existe otro trámite con el nombre '{clean_name}' en esta área.",
                    )
            tramite.nombre = clean_name
        if data.descripcion is not None:
            tramite.descripcion = data.descripcion.strip() if data.descripcion else None
        if data.documentacion_requerida is not None:
            tramite.documentacion_requerida = data.documentacion_requerida.strip()
        if data.requerimientos_previos is not None:
            tramite.requerimientos_previos = data.requerimientos_previos.strip() if data.requerimientos_previos else None
        if data.emite_carnet is not None:
            tramite.emite_carnet = data.emite_carnet
        if data.limite_sobreturnos_diarios is not None:
            tramite.limite_sobreturnos_diarios = data.limite_sobreturnos_diarios
        await db.commit()
        await db.refresh(tramite)
        return tramite

    @staticmethod
    async def delete_tramite(db: AsyncSession, tramite_id: int) -> None:
        tramite = await CatalogService.get_tramite_by_id(db, tramite_id)

        turnos_count = await db.scalar(
            select(func.count()).select_from(Turno).where(Turno.tramite_id == tramite_id)
        )
        if turnos_count and turnos_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se puede eliminar el trámite porque posee turnos asociados.",
            )

        await db.delete(tramite)
        await db.commit()
