import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status

from app.models.agenda_configuracion import AgendaConfiguracion
from app.models.role import Role
from app.models.turno import Turno
from app.models.user import User
from app.models.variante import Variante
from app.schemas.turno import TurnoCreateRequest
from app.services.turno_service import TurnoService


@pytest.mark.asyncio
async def test_cancel_turno_ciudadano_24h_rule_success():
    """Ciudadano puede cancelar con >= 24h de anticipación."""
    db = AsyncMock()
    ciudadano = User(id=1, nombre="Juan", apellido="Perez", rol=Role(id=1, nombre="CIUDADANO"))

    futuro_remoto = datetime.now(timezone.utc) + timedelta(hours=48)
    turno = Turno(
        id=uuid.uuid4(),
        ciudadano_id=1,
        tramite_id=10,
        fecha_hora_inicio=futuro_remoto,
        fecha_hora_fin=futuro_remoto + timedelta(minutes=30),
        estado="RESERVADO",
        ciudadano=ciudadano,
        created_at=datetime.now(timezone.utc),
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = turno
    db.execute.return_value = mock_res

    res = await TurnoService.cancel_turno(db, ciudadano, turno.id)
    assert res.estado == "CANCELADO"
    assert res.cancelado_por_id == 1


@pytest.mark.asyncio
async def test_cancel_turno_ciudadano_less_than_24h_fails():
    """Ciudadano NO puede cancelar con < 24h de anticipación."""
    db = AsyncMock()
    ciudadano = User(id=1, nombre="Juan", apellido="Perez", rol=Role(id=1, nombre="CIUDADANO"))

    futuro_cercano = datetime.now(timezone.utc) + timedelta(hours=10)
    turno = Turno(
        id=uuid.uuid4(),
        ciudadano_id=1,
        tramite_id=10,
        fecha_hora_inicio=futuro_cercano,
        fecha_hora_fin=futuro_cercano + timedelta(minutes=30),
        estado="RESERVADO",
        ciudadano=ciudadano,
        created_at=datetime.now(timezone.utc),
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = turno
    db.execute.return_value = mock_res

    with pytest.raises(HTTPException) as exc_info:
        await TurnoService.cancel_turno(db, ciudadano, turno.id)
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "24 horas" in exc_info.value.detail


@pytest.mark.asyncio
async def test_cancel_turno_admin_optional_reason():
    """El motivo_cancelacion es opcional al cancelar un turno."""
    db = AsyncMock()
    admin = User(id=2, nombre="Admin", apellido="Municipal", rol=Role(id=2, nombre="ADMINISTRATIVO"))

    futuro = datetime.now(timezone.utc) + timedelta(hours=5)
    turno = Turno(
        id=uuid.uuid4(),
        ciudadano_id=1,
        tramite_id=10,
        fecha_hora_inicio=futuro,
        fecha_hora_fin=futuro + timedelta(minutes=30),
        estado="RESERVADO",
        ciudadano=User(id=1, nombre="Juan", apellido="Perez"),
        created_at=datetime.now(timezone.utc),
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = turno
    db.execute.return_value = mock_res

    # Cancelar sin motivo (motivo_cancelacion vacio o None)
    res_sin_motivo = await TurnoService.cancel_turno(db, admin, turno.id, motivo_cancelacion="")
    assert res_sin_motivo.estado == "CANCELADO"
    assert res_sin_motivo.motivo_cancelacion is None

    # Cancelar con motivo
    turno.estado = "RESERVADO"
    res_con_motivo = await TurnoService.cancel_turno(db, admin, turno.id, motivo_cancelacion="Falta de insumos")
    assert res_con_motivo.estado == "CANCELADO"
    assert res_con_motivo.motivo_cancelacion == "Falta de insumos"


@pytest.mark.asyncio
async def test_create_turno_conflict_409():
    """Validar que si la capacidad simultánea fue ocupada, devuelva 409 Conflict."""
    db = AsyncMock()
    user = User(id=1, nombre="Juan", apellido="Perez", rol=Role(id=1, nombre="CIUDADANO"))

    variantes = [Variante(id=1, tramite_id=10, duracion_minutos=30)]
    target_dt = (datetime.now(timezone.utc) + timedelta(days=7)).replace(hour=12, minute=0, second=0, microsecond=0)
    agenda = AgendaConfiguracion(
        id=1,
        tramite_id=10,
        dia_semana=target_dt.isoweekday(),
        hora_inicio="08:00",
        hora_fin="18:00",
        capacidad_simultanea=1,
        activo=True,
    )

    # Mock availability check & overlapping turnos returning 1 existing overlapping turno
    with patch("app.services.turno_service.AvailabilityService.validate_tramite_and_variantes", return_value=variantes):
        mock_agenda_res = MagicMock()
        mock_agenda_res.scalar_one_or_none.return_value = agenda

        mock_turnos_res = MagicMock()
        mock_turnos_res.scalars.return_value.all.return_value = [
            Turno(id=uuid.uuid4(), tramite_id=10, estado="RESERVADO")
        ]

        db.execute.side_effect = [mock_agenda_res, mock_turnos_res]

        req = TurnoCreateRequest(
            tramite_id=10,
            variante_ids=[1],
            fecha_hora_inicio=target_dt,
        )

        with pytest.raises(HTTPException) as exc_info:
            await TurnoService.create_turno(db, user, req)
        assert exc_info.value.status_code == status.HTTP_409_CONFLICT

