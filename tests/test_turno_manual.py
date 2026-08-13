import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.role import Role
from app.models.tramite import Tramite
from app.models.turno import Turno
from app.models.user import User
from app.schemas.turno import DatosRegistroInmediato, TurnoCreateRequest
from app.services.turno_service import TurnoService


@pytest.mark.asyncio
async def test_crear_turno_manual_registro_al_vuelo():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    admin = User(id=1, nombre="Operador", apellido="Municipal", rol=Role(id=2, nombre="ADMINISTRATIVO"))
    tramite = Tramite(id=10, nombre="Licencia B1")

    # Mock availability check
    mock_variante = MagicMock(id=1, duracion_minutos=15)

    dt_test = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
    data = TurnoCreateRequest(
        tramite_id=10,
        variante_ids=[1],
        fecha_hora_inicio=dt_test,
        datos_registro_inmediato=DatosRegistroInmediato(
            dni="40123456",
            email="nuevo.ciudadano@email.com",
            telefono="3471001122",
            nombre="Carlos",
            apellido="Gomez",
        ),
    )

    # Mock user search by DNI HMAC -> not found
    mock_usr_res = MagicMock()
    mock_usr_res.scalar_one_or_none.return_value = None

    # Mock agenda check
    mock_agenda = MagicMock(hora_inicio="07:00", hora_fin="14:00", capacidad_simultanea=2)
    mock_agenda_res = MagicMock()
    mock_agenda_res.scalar_one_or_none.return_value = mock_agenda

    # Mock overlapping turnos
    mock_turnos_res = MagicMock()
    mock_turnos_res.scalars.return_value.all.return_value = []

    db.execute.side_effect = [mock_usr_res, MagicMock(scalar_one_or_none=lambda: Role(id=1, nombre="ciudadano")), mock_agenda_res, mock_turnos_res]

    fake_turno = Turno(
        id=uuid.uuid4(),
        ciudadano_id=99,
        tramite_id=10,
        fecha_hora_inicio=dt_test,
        fecha_hora_fin=dt_test + timedelta(minutes=15),
        estado="RESERVADO",
        es_sobreturno=False,
        ciudadano=User(id=99, nombre="Carlos", apellido="Gomez", dni_cifrado="cifrado", estado="PENDING_VALIDATION"),
        tramite=tramite,
        variantes=[mock_variante],
        created_at=datetime.now(timezone.utc),
    )

    with patch("app.services.availability_service.AvailabilityService.validate_tramite_and_variantes", return_value=[mock_variante]):
        with patch("app.services.turno_service.TurnoService.get_turno_by_id", return_value=fake_turno):
            res = await TurnoService.create_turno(db, admin, data)
            assert res.id == fake_turno.id
            assert db.add.called


@pytest.mark.asyncio
async def test_list_turnos_filtros_search_y_dni():
    db = AsyncMock()
    admin = User(id=1, nombre="Admin", apellido="User", rol=Role(id=2, nombre="ADMINISTRATIVO"))
    ciudadano = User(id=5, nombre="Maria", apellido="Gonzalez", dni_cifrado="cifrado", rol=Role(id=1, nombre="CIUDADANO"))
    tramite = Tramite(id=10, nombre="Trámite test")

    t1 = Turno(
        id=uuid.uuid4(),
        ciudadano_id=5,
        tramite_id=10,
        fecha_hora_inicio=datetime.now(timezone.utc),
        fecha_hora_fin=datetime.now(timezone.utc) + timedelta(minutes=30),
        estado="RESERVADO",
        es_sobreturno=False,
        ciudadano=ciudadano,
        tramite=tramite,
        variantes=[],
        created_at=datetime.now(timezone.utc),
    )

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [t1]
    db.execute.return_value = mock_res

    with patch("app.services.turno_service.decrypt_pii", return_value="40123456"):
        res = await TurnoService.list_turnos(db, admin, dni="40123456", search="Maria")
        assert len(res) == 1
        assert res[0].ciudadano_dni == "40123456"
