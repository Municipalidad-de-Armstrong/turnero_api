from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status
from httpx import AsyncClient

from app.models.area import Area
from app.schemas.area import AreaCreateRequest, AreaResponse
from app.schemas.tramite import TramiteCreateRequest, TramiteResponse
from app.services.catalog_service import CatalogService


@pytest.mark.asyncio
async def test_catalog_service_area_crud():
    """Unit test for Area CRUD in CatalogService."""
    db = AsyncMock()

    # Mock get_all_areas
    mock_result_all = MagicMock()
    mock_result_all.scalars.return_value.all.return_value = [
        Area(
            id=1,
            nombre="Tránsito",
            descripcion="Licencias",
            direccion="San Martín 1790",
            created_at=datetime.now(timezone.utc),
        )
    ]
    db.execute.return_value = mock_result_all

    areas = await CatalogService.get_all_areas(db)
    assert len(areas) == 1
    assert areas[0].nombre == "Tránsito"
    assert areas[0].direccion == "San Martín 1790"

    # Mock create_area (existing conflict)
    mock_existing = MagicMock()
    mock_existing.scalar_one_or_none.return_value = Area(id=1, nombre="Tránsito")
    db.execute.return_value = mock_existing

    with pytest.raises(HTTPException) as exc_info:
        await CatalogService.create_area(
            db, AreaCreateRequest(nombre="Tránsito", descripcion="Licencias", direccion="San Martín 1790")
        )
    assert exc_info.value.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_catalog_service_delete_area_in_use():
    """Test delete_area fails with 409 when area has associated tramites."""
    db = AsyncMock()
    # Mock area exists
    mock_area = MagicMock()
    mock_area.scalar_one_or_none.return_value = Area(id=1, nombre="Tránsito")

    # Mock tramites exist for area
    mock_tramites = MagicMock()
    mock_tramites.scalars.return_value.first.return_value = MagicMock()

    db.execute.side_effect = [mock_area, mock_tramites]

    with pytest.raises(HTTPException) as exc_info:
        await CatalogService.delete_area(db, 1)

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert "contiene trámites asociados" in exc_info.value.detail


@pytest.mark.asyncio
async def test_catalog_service_tramite_crud():
    """Unit test for Tramite CRUD in CatalogService."""
    db = AsyncMock()
    db.add = MagicMock()

    # Mock get_tramite_by_id (not found)
    mock_result_none = MagicMock()
    mock_result_none.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result_none

    with pytest.raises(HTTPException) as exc_info:
        await CatalogService.get_tramite_by_id(db, 999)
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    # Mock area existing and tramite creation
    mock_area = MagicMock()
    mock_area.scalar_one_or_none.return_value = Area(id=1, nombre="Tránsito")
    mock_none_tramite = MagicMock()
    mock_none_tramite.scalar_one_or_none.return_value = None
    db.execute.side_effect = [mock_area, mock_none_tramite]

    tramite = await CatalogService.create_tramite(
        db,
        TramiteCreateRequest(
            area_id=1,
            nombre="Carnet B1",
            documentacion_requerida="DNI original",
            emite_carnet=True,
            limite_sobreturnos_diarios=5,
        ),
    )
    assert tramite.nombre == "Carnet B1"
    assert tramite.emite_carnet is True


@pytest.mark.asyncio
async def test_api_list_areas(client: AsyncClient):
    """Test GET /api/v1/areas public endpoint."""
    with patch("app.services.catalog_service.CatalogService.get_all_areas") as mock_get:
        mock_get.return_value = [
            AreaResponse(
                id=1,
                nombre="Rentas",
                descripcion="Impuestos municipales",
                created_at=datetime.now(timezone.utc),
            )
        ]

        res = await client.get("/api/v1/areas")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["nombre"] == "Rentas"


@pytest.mark.asyncio
async def test_api_list_tramites(client: AsyncClient):
    """Test GET /api/v1/tramites public endpoint."""
    with patch("app.services.catalog_service.CatalogService.get_all_tramites") as mock_get:
        mock_get.return_value = [
            TramiteResponse(
                id=10,
                area_id=1,
                nombre="Pago TGI",
                descripcion="Pago de tasa general inmueble",
                documentacion_requerida="DNI y cedula catastral",
                requerimientos_previos=None,
                emite_carnet=False,
                limite_sobreturnos_diarios=5,
                created_at=datetime.now(timezone.utc),
            )
        ]

        res = await client.get("/api/v1/tramites")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["nombre"] == "Pago TGI"
        assert data[0]["emite_carnet"] is False
