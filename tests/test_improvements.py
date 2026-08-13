from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Request, status

from app.core.rate_limit import RateLimiter
from app.models.turno import Turno
from app.services.catalog_subresources_service import CatalogSubresourcesService


def test_turno_indexes_defined():
    """Verifica que los índices compuestos requeridos estén declarados en __table_args__ de Turno."""
    table_args = getattr(Turno, "__table_args__", ())
    index_names = {idx.name for idx in table_args if hasattr(idx, "name")}

    assert "idx_turnos_disponibilidad" in index_names
    assert "idx_turnos_ciudadano" in index_names
    assert "idx_turnos_fecha" in index_names


@pytest.mark.asyncio
async def test_magic_bytes_validation_rejects_fake_pdf():
    """Verifica que el servicio de subida rechace archivos con extensión .pdf pero sin firma binaria %PDF-."""
    db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = MagicMock()
    db.execute.return_value = mock_res

    fake_file = AsyncMock()
    fake_file.filename = "script_malicioso.pdf"
    fake_file.read.return_value = b"MZ\x90\x00\x03\x00\x00\x00"  # Executable PE header

    with pytest.raises(HTTPException) as exc_info:
        await CatalogSubresourcesService.upload_documento(
            db, tramite_id=1, nombre="Formulario Fake", archivo=fake_file
        )
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "firma binaria" in exc_info.value.detail


@pytest.mark.asyncio
async def test_rate_limiter_blocks_excessive_requests():
    """Verifica que RateLimiter devuelva HTTP 429 cuando se supera el número de peticiones permitidas."""
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    request = MagicMock(spec=Request)
    request.client.host = "192.168.1.100"
    request.headers = {}
    request.url.path = "/api/v1/auth/tokens"

    await limiter(request)
    await limiter(request)

    with pytest.raises(HTTPException) as exc_info:
        await limiter(request)
    assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
