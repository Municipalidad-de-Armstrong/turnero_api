import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status
from httpx import AsyncClient

from app.core.uploads import fs_path_to_url, url_to_fs_path
from app.models.tramite import Tramite
from app.models.tramite_documento import TramiteDocumento, delete_file_from_disk
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


# ---------------- Helpers URL <-> filesystem ----------------

def test_url_fs_roundtrip():
    fs = os.path.join("uploads", "tramites", "abc123.pdf")
    url = fs_path_to_url(fs)
    assert url == "/static/uploads/tramites/abc123.pdf"
    # Vuelta atrás: url_to_fs_path debe reconstruir el path de disco.
    back = url_to_fs_path(url)
    assert back.replace("\\", "/") == "uploads/tramites/abc123.pdf"


def test_url_to_fs_path_handles_legacy_url():
    """Filas pre-fix guardaban la URL literal; el helper debe igual resolverlas."""
    back = url_to_fs_path("/static/uploads/tramites/ad21df7c.pdf")
    assert back.replace("\\", "/") == "uploads/tramites/ad21df7c.pdf"


# ---------------- Borrado físico de archivo en disco (regresión) ----------------

@pytest.mark.asyncio
async def test_upload_and_delete_removes_physical_file(tmp_path):
    """Regresión del bug: al borrar un documento, su archivo físico en disco también
    debe desaparecer (antes el listener trataba la URL como path FS y nunca borraba)."""
    db = AsyncMock()
    # AsyncSession.add() es sincrónico en SQLAlchemy async (no devuelve coroutine);
    # lo modelamos con MagicMock para que no genere el RuntimeWarning de coroutine
    # nunca awaiteada.
    db.add = MagicMock()

    # El trámite existe.
    mock_tramite = MagicMock()
    mock_tramite.scalar_one_or_none.return_value = Tramite(id=1, nombre="Licencia B1")

    async def fake_execute(stmt):
        return mock_tramite

    async def fake_delete(obj):
        # Simula el flush de SQLAlchemy que dispara el listener after_delete.
        delete_file_from_disk(None, None, obj)

    db.execute.side_effect = fake_execute
    db.delete.side_effect = fake_delete

    mock_upload = AsyncMock()
    mock_upload.filename = "formulario.pdf"
    mock_upload.read.return_value = b"%PDF-1.4 fake content"

    # Redirigimos el directorio de uploads a un tmp_path controlado.
    with patch(
        "app.services.catalog_subresources_service.UPLOADS_DIR",
        os.path.join(str(tmp_path), "tramites"),
    ), patch(
        "app.core.uploads.settings.UPLOAD_DIR", str(tmp_path)
    ):
        doc = await CatalogSubresourcesService.upload_documento(
            db, 1, "Formulario DDJJ", mock_upload
        )

        # El archivo físico existe tras subirlo.
        fs_path = url_to_fs_path(doc.ruta_archivo)
        assert os.path.exists(fs_path), "el archivo subido debe existir en disco"

        # Simular el SELECT del documento para borrarlo.
        mock_doc = MagicMock()
        mock_doc.scalar_one_or_none.return_value = doc

        async def fake_select_result(stmt):
            return mock_doc

        db.execute.side_effect = fake_select_result

        await CatalogSubresourcesService.delete_documento(db, 1, doc.id)

        # El archivo físico debe haberse borrado del disco.
        assert not os.path.exists(fs_path), (
            "el listener after_delete debe borrar el archivo físico del disco"
        )
