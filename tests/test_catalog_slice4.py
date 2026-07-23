from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import HTTPException, status
from httpx import AsyncClient

from app.models.tramite import Tramite
from app.models.tramite_documento import TramiteDocumento
from app.models.tramite_enlace import TramiteEnlace
from app.schemas.tramite_enlace import (
    TramiteEnlaceCreateRequest,
)
from app.schemas.variante import (
    VarianteCreateRequest,
)
from app.services.catalog_subresources_service import CatalogSubresourcesService


@pytest.mark.asyncio
async def test_variante_service_unit():
    db = AsyncMock()
    db.add = MagicMock()


    # 1. Tramite no existe -> 404
    mock_none = MagicMock()
    mock_none.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_none

    with pytest.raises(HTTPException) as exc:
        await CatalogSubresourcesService.create_variante(
            db, 999, VarianteCreateRequest(nombre="Test", duracion_minutos=15)
        )
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND

    # 2. Crear variante exitosa
    mock_tramite = MagicMock()
    mock_tramite.scalar_one_or_none.return_value = Tramite(id=1, nombre="Licencia B1")
    db.execute.return_value = mock_tramite

    v = await CatalogSubresourcesService.create_variante(
        db, 1, VarianteCreateRequest(nombre="Examen Teórico", duracion_minutos=30)
    )
    assert v.nombre == "Examen Teórico"
    assert v.duracion_minutos == 30


@pytest.mark.asyncio
async def test_documento_invalid_file_extension():
    db = AsyncMock()
    mock_tramite = MagicMock()
    mock_tramite.scalar_one_or_none.return_value = Tramite(id=1, nombre="Licencia B1")
    db.execute.return_value = mock_tramite

    mock_upload = AsyncMock()
    mock_upload.filename = "script.exe"
    mock_upload.read.return_value = b"exe content"

    with pytest.raises(HTTPException) as exc:
        await CatalogSubresourcesService.upload_documento(
            db, 1, "Script Malicioso", mock_upload
        )
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "no permitido" in exc.value.detail


@pytest.mark.asyncio
async def test_enlace_service_unit():
    db = AsyncMock()
    db.add = MagicMock()

    mock_tramite = MagicMock()
    mock_tramite.scalar_one_or_none.return_value = Tramite(id=1, nombre="Licencia B1")
    db.execute.return_value = mock_tramite

    enlace = await CatalogSubresourcesService.create_enlace(
        db,
        1,
        TramiteEnlaceCreateRequest(
            descripcion="Consultar Multas", url="https://multas.gov.ar"
        ),
    )
    assert enlace.descripcion == "Consultar Multas"
    assert enlace.url == "https://multas.gov.ar"


@pytest.mark.asyncio
async def test_api_list_tramite_documentos(client: AsyncClient):
    with patch(
        "app.services.catalog_subresources_service.CatalogSubresourcesService.get_documentos_by_tramite"
    ) as mock_get:
        mock_get.return_value = [
            TramiteDocumento(
                id=1,
                tramite_id=10,
                nombre="Formulario DDJJ",
                ruta_archivo="/static/uploads/tramites/abc.pdf",
                created_at=datetime.now(timezone.utc),
            )
        ]

        res = await client.get("/api/v1/tramites/10/documentos")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["nombre"] == "Formulario DDJJ"


@pytest.mark.asyncio
async def test_api_list_tramite_enlaces(client: AsyncClient):
    with patch(
        "app.services.catalog_subresources_service.CatalogSubresourcesService.get_enlaces_by_tramite"
    ) as mock_get:
        mock_get.return_value = [
            TramiteEnlace(
                id=1,
                tramite_id=10,
                descripcion="Link Multas",
                url="https://armstrong.gov.ar",
                created_at=datetime.now(timezone.utc),
            )
        ]

        res = await client.get("/api/v1/tramites/10/enlaces")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["descripcion"] == "Link Multas"
