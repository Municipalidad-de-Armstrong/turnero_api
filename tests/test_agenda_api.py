from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import HTTPException, status
from pydantic import ValidationError

from app.models.agenda_configuracion import AgendaConfiguracion
from app.models.tramite import Tramite
from app.schemas.agenda import AgendaConfigSaveItem
from app.services.agenda_service import AgendaService


def test_agenda_schema_validation():
    """Valida que Pydantic devuelva error de validación si hora_fin <= hora_inicio o día fuera de rango."""
    with pytest.raises(ValidationError):
        AgendaConfigSaveItem(
            dia_semana=1,
            hora_inicio="12:00",
            hora_fin="08:00",
            capacidad_simultanea=2,
            activo=True,
        )

    with pytest.raises(ValidationError):
        AgendaConfigSaveItem(
            dia_semana=7,
            hora_inicio="08:00",
            hora_fin="12:00",
            capacidad_simultanea=1,
            activo=True,
        )

    item = AgendaConfigSaveItem(
        dia_semana=1,
        hora_inicio="08:00",
        hora_fin="12:00",
        capacidad_simultanea=2,
        activo=True,
    )
    assert item.dia_semana == 1
    assert item.hora_inicio == "08:00"
    assert item.hora_fin == "12:00"


@pytest.mark.asyncio
async def test_agenda_service_tramite_not_found():
    """Valida que si el trámite no existe devuelva 404."""
    db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_res

    with pytest.raises(HTTPException) as exc_info:
        await AgendaService.get_agenda_config(db, 999)
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_agenda_service_duplicate_days():
    """Valida que si se envían días duplicados devuelva 400 Bad Request."""
    db = AsyncMock()
    mock_tramite = MagicMock()
    mock_tramite.scalar_one_or_none.return_value = Tramite(id=1, nombre="Licencia")
    db.execute.return_value = mock_tramite

    items = [
        AgendaConfigSaveItem(dia_semana=1, hora_inicio="08:00", hora_fin="12:00", capacidad_simultanea=1, activo=True),
        AgendaConfigSaveItem(dia_semana=1, hora_inicio="13:00", hora_fin="17:00", capacidad_simultanea=1, activo=True),
    ]

    with pytest.raises(HTTPException) as exc_info:
        await AgendaService.save_agenda_config(db, 1, items)
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
@patch("app.services.agenda_service.get_redis_client")
async def test_agenda_service_save_and_cache(mock_get_redis):
    """Valida que la creación/actualización guarde en DB y limpie el caché Redis."""
    redis_mock = AsyncMock()
    mock_get_redis.return_value = redis_mock

    db = AsyncMock()
    mock_tramite = MagicMock()
    mock_tramite.scalar_one_or_none.return_value = Tramite(id=1, nombre="Licencia")

    mock_db_items = MagicMock()
    mock_db_items.scalars.return_value.all.return_value = [
        AgendaConfiguracion(
            id=10, tramite_id=1, dia_semana=1, hora_inicio="08:00", hora_fin="12:00", capacidad_simultanea=2, activo=True
        )
    ]
    db.execute.side_effect = [mock_tramite, None, mock_db_items]

    items = [
        AgendaConfigSaveItem(dia_semana=1, hora_inicio="08:00", hora_fin="12:00", capacidad_simultanea=2, activo=True)
    ]

    res = await AgendaService.save_agenda_config(db, 1, items)
    assert len(res) == 1
    assert res[0].dia_semana == 1
    redis_mock.delete.assert_called_once_with("agenda_config:1")
