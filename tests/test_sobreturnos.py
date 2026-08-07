import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import HTTPException, status

from app.models.role import Role
from app.models.tramite import Tramite
from app.models.turno import Turno
from app.models.user import User
from app.schemas.turno import SobreturnoCreateRequest, DatosRegistroInmediato
from app.services.operation_service import OperationService


@pytest.mark.asyncio
async def test_crear_sobreturno_exitoso():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    admin = User(id=1, nombre="Admin", apellido="User", rol=Role(id=2, nombre="ADMINISTRATIVO"))
    ciudadano = User(id=5, nombre="Juan", apellido="Perez", dni_cifrado="dummy", rol=Role(id=1, nombre="CIUDADANO"))
    tramite = Tramite(id=10, nombre="Licencia de Conducir", limite_sobreturnos_diarios=5)

    db.get.side_effect = lambda model, pk: tramite if model == Tramite else (ciudadano if pk == 5 else None)

    mock_count_res = MagicMock()
    mock_count_res.scalars.return_value.all.return_value = []
    db.execute.return_value = mock_count_res

    data = SobreturnoCreateRequest(
        tramite_id=10,
        fecha=date.today().isoformat(),
        prioridad="ALTA",
        ciudadano_id=5,
    )

    fake_turno = Turno(
        id=uuid.uuid4(),
        ciudadano_id=5,
        tramite_id=10,
        fecha_hora_inicio=datetime.now(timezone.utc),
        fecha_hora_fin=datetime.now(timezone.utc) + timedelta(minutes=30),
        estado="RESERVADO",
        es_sobreturno=True,
        sobreturno_prioridad="ALTA",
        ciudadano=ciudadano,
        tramite=tramite,
        variantes=[],
    )

    with patch("app.services.turno_service.TurnoService.get_turno_by_id", return_value=fake_turno):
        res = await OperationService.crear_sobreturno(db, data, admin)
        assert res.es_sobreturno is True
        assert res.sobreturno_prioridad == "ALTA"
        assert db.add.called


@pytest.mark.asyncio
async def test_crear_sobreturno_excede_limite_diario():
    db = AsyncMock()
    admin = User(id=1, nombre="Admin", apellido="User", rol=Role(id=2, nombre="ADMINISTRATIVO"))
    tramite = Tramite(id=10, nombre="Trámite Con Límite", limite_sobreturnos_diarios=2)

    db.get.side_effect = lambda model, pk: tramite if model == Tramite else None

    # Simular que ya existen 2 sobreturnos cargados en el día
    existing_sobreturnos = [
        Turno(id=uuid.uuid4(), tramite_id=10, es_sobreturno=True, estado="RESERVADO"),
        Turno(id=uuid.uuid4(), tramite_id=10, es_sobreturno=True, estado="RESERVADO"),
    ]
    mock_count_res = MagicMock()
    mock_count_res.scalars.return_value.all.return_value = existing_sobreturnos
    db.execute.return_value = mock_count_res

    data = SobreturnoCreateRequest(
        tramite_id=10,
        fecha=date.today().isoformat(),
        prioridad="BAJA",
        ciudadano_id=5,
    )

    with pytest.raises(HTTPException) as exc_info:
        await OperationService.crear_sobreturno(db, data, admin)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Límite diario de sobreturnos alcanzado" in exc_info.value.detail
