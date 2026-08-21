from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status

from app.models.agenda_configuracion import AgendaConfiguracion
from app.models.tramite import Tramite
from app.models.turno import Turno
from app.models.variante import Variante
from app.services.availability_service import LOCAL_TZ, AvailabilityService


@pytest.mark.asyncio
async def test_validate_tramite_and_variantes_empty_list():
    db = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        await AvailabilityService.validate_tramite_and_variantes(db, 1, [])
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_validate_tramite_and_variantes_tramite_not_found():
    db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_res

    with pytest.raises(HTTPException) as exc:
        await AvailabilityService.validate_tramite_and_variantes(db, 99, [1])
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_validate_tramite_and_variantes_mismatched_tramite():
    db = AsyncMock()
    mock_tramite = MagicMock()
    mock_tramite.scalar_one_or_none.return_value = Tramite(id=1, nombre="Test")

    mock_vars = MagicMock()
    mock_vars.scalars.return_value.all.return_value = [
        Variante(id=10, tramite_id=2, nombre="V1", duracion_minutos=15)
    ]
    db.execute.side_effect = [mock_tramite, mock_vars]

    with pytest.raises(HTTPException) as exc:
        await AvailabilityService.validate_tramite_and_variantes(db, 1, [10])
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_get_disponibilidad_no_agenda():
    db = AsyncMock()
    mock_tramite = MagicMock()
    mock_tramite.scalar_one_or_none.return_value = Tramite(id=1, nombre="Test")

    mock_vars = MagicMock()
    mock_vars.scalars.return_value.all.return_value = [
        Variante(id=10, tramite_id=1, nombre="V1", duracion_minutos=30)
    ]
    mock_agenda = MagicMock()
    mock_agenda.scalar_one_or_none.return_value = None

    db.execute.side_effect = [mock_tramite, mock_vars, mock_agenda]

    res = await AvailabilityService.get_disponibilidad(
        db, 1, date(2026, 8, 10), [10]
    )
    assert res == []


@pytest.mark.asyncio
async def test_get_disponibilidad_with_capacity_and_overlap():
    db = AsyncMock()
    mock_tramite = MagicMock()
    mock_tramite.scalar_one_or_none.return_value = Tramite(id=1, nombre="Test")

    mock_vars = MagicMock()
    mock_vars.scalars.return_value.all.return_value = [
        Variante(id=10, tramite_id=1, nombre="V1", duracion_minutos=30)
    ]
    mock_agenda = MagicMock()
    target_date = date.today() + timedelta(days=7)
    agenda_obj = AgendaConfiguracion(
        id=1,
        tramite_id=1,
        dia_semana=target_date.isoweekday(),
        hora_inicio="08:00",
        hora_fin="09:00",
        capacidad_simultanea=1,
        activo=True,
    )
    mock_agenda.scalar_one_or_none.return_value = agenda_obj

    # Existing turno from 08:00 to 08:30 (local time)
    t_start = datetime.combine(target_date, time(8, 0), tzinfo=LOCAL_TZ).astimezone(timezone.utc)
    t_end = datetime.combine(target_date, time(8, 30), tzinfo=LOCAL_TZ).astimezone(timezone.utc)
    existing_turno = Turno(
        tramite_id=1,
        fecha_hora_inicio=t_start,
        fecha_hora_fin=t_end,
        estado="RESERVADO",
        es_sobreturno=False,
    )

    mock_turnos = MagicMock()
    mock_turnos.scalars.return_value.all.return_value = [existing_turno]

    db.execute.side_effect = [
        mock_tramite,
        mock_vars,
        mock_agenda,
        mock_turnos,
    ]

    res = await AvailabilityService.get_disponibilidad(
        db, 1, target_date, [10]
    )


    # 08:00-08:30 (occupied by capacity 1 -> disponible False)
    # 08:15-08:45 (overlaps existing turno -> disponible False)
    # 08:30-09:00 (no overlap -> disponible True)
    assert len(res) == 3
    assert res[0].disponible is False
    assert res[1].disponible is False
    assert res[2].disponible is True


@pytest.mark.asyncio
async def test_get_primer_turno_disponible_not_found():
    db = AsyncMock()
    mock_validate = patch.object(
        AvailabilityService,
        "validate_tramite_and_variantes",
        new=AsyncMock(return_value=[]),
    )
    mock_disp = patch.object(
        AvailabilityService,
        "get_disponibilidad",
        new=AsyncMock(return_value=[]),
    )

    with mock_validate, mock_disp:
        with pytest.raises(HTTPException) as exc:
            await AvailabilityService.get_primer_turno_disponible(db, 1, [10])
        assert exc.value.status_code == status.HTTP_404_NOT_FOUND
