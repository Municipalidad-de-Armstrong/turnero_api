import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status

from app.models.role import Role
from app.models.tramite import Tramite
from app.models.turno import Turno
from app.models.user import User
from app.schemas.turno import SobreturnoCreateRequest
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
    mock_count_res.scalar_one_or_none.return_value = None
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


@pytest.mark.asyncio
async def test_list_turnos_includes_sobreturnos_with_date_filter():
    """Verifica que list_turnos retorne sobreturnos al filtrar por fecha_desde y fecha_hasta."""
    from app.services.turno_service import TurnoService
    db = AsyncMock()
    admin = User(id=1, nombre="Admin", apellido="User", rol=Role(id=2, nombre="ADMINISTRATIVO"))
    ciudadano = User(id=5, nombre="Juan", apellido="Perez", dni_cifrado="dummy", rol=Role(id=1, nombre="CIUDADANO"))
    tramite = Tramite(id=10, nombre="Licencia", limite_sobreturnos_diarios=5)

    today = date.today()
    start_dt = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=3)
    fake_sobreturno = Turno(
        id=uuid.uuid4(),
        ciudadano_id=5,
        tramite_id=10,
        fecha_hora_inicio=start_dt,
        fecha_hora_fin=start_dt + timedelta(hours=1),
        estado="RESERVADO",
        es_sobreturno=True,
        sobreturno_prioridad="ALTA",
        ciudadano=ciudadano,
        tramite=tramite,
        variantes=[],
    )

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [fake_sobreturno]
    db.execute.return_value = mock_res

    with patch("app.services.turno_service.decrypt_pii", return_value="12345678"):
        res = await TurnoService.list_turnos(
            db=db,
            current_user=admin,
            fecha_desde=datetime.combine(today, datetime.min.time()),
            fecha_hasta=datetime.combine(today, datetime.min.time()),
        )
        assert len(res) == 1
        assert res[0].es_sobreturno is True
        assert res[0].sobreturno_prioridad == "ALTA"


@pytest.mark.asyncio
async def test_crear_sobreturno_toma_hora_fin_agenda():
    """Verifica que el sobreturno tome como hora de inicio la hora_fin de la agenda configurada."""
    from app.models.agenda_configuracion import AgendaConfiguracion
    from app.services.availability_service import LOCAL_TZ

    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    admin = User(id=1, nombre="Admin", apellido="User", rol=Role(id=2, nombre="ADMINISTRATIVO"))
    ciudadano = User(id=5, nombre="Juan", apellido="Perez", dni_cifrado="dummy", rol=Role(id=1, nombre="CIUDADANO"))
    tramite = Tramite(id=10, nombre="Licencia de Conducir", limite_sobreturnos_diarios=5)

    db.get.side_effect = lambda model, pk: tramite if model == Tramite else (ciudadano if pk == 5 else None)

    agenda_lunes = AgendaConfiguracion(
        id=1, tramite_id=10, dia_semana=1, hora_inicio="08:00", hora_fin="14:00", activo=True
    )

    mock_count_res = MagicMock()
    mock_count_res.scalars.return_value.all.return_value = []

    mock_agenda_res = MagicMock()
    mock_agenda_res.scalar_one_or_none.return_value = agenda_lunes

    db.execute.side_effect = [mock_count_res, mock_agenda_res]

    fecha_test = date(2026, 8, 24)  # Lunes
    data = SobreturnoCreateRequest(
        tramite_id=10,
        fecha=fecha_test.isoformat(),
        prioridad="ALTA",
        ciudadano_id=5,
    )

    async def fake_get_turno_by_id(db_session, user, turno_id):
        # Inspect the added Turno
        added_turno = db.add.call_args[0][0]
        return added_turno

    with patch("app.services.turno_service.TurnoService.get_turno_by_id", side_effect=fake_get_turno_by_id):
        res = await OperationService.crear_sobreturno(db, data, admin)
        # Convert start time to local timezone to check hour
        local_dt = res.fecha_hora_inicio.astimezone(LOCAL_TZ)
        assert local_dt.hour == 14
        assert local_dt.minute == 0


