import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import HTTPException, status

from app.models.role import Role
from app.models.tramite import Tramite
from app.models.turno import Turno
from app.models.user import User
from app.schemas.turno import TurnoResultadoRequest
from app.services.operation_service import OperationService


@pytest.mark.asyncio
async def test_get_cola_dia_ordering():
    """Verifica que los turnos regulares se ordenen cronológicamente y los sobreturnos al final por prioridad."""
    db = AsyncMock()
    now_utc = datetime.now(timezone.utc)

    ciudadano = User(
        id=2,
        nombre="Pedro",
        apellido="Gomez",
        dni_cifrado="dummy_encrypted",
        telefono_cifrado="dummy_phone",
        rol=Role(id=1, nombre="CIUDADANO"),
    )
    tramite = Tramite(id=10, nombre="Licencia B1", emite_carnet=True)

    turno_reg_2 = Turno(
        id=uuid.uuid4(),
        ciudadano_id=2,
        tramite_id=10,
        fecha_hora_inicio=now_utc + timedelta(hours=2),
        fecha_hora_fin=now_utc + timedelta(hours=2, minutes=30),
        estado="RESERVADO",
        es_sobreturno=False,
        ciudadano=ciudadano,
        tramite=tramite,
        variantes=[],
    )

    turno_reg_1 = Turno(
        id=uuid.uuid4(),
        ciudadano_id=2,
        tramite_id=10,
        fecha_hora_inicio=now_utc + timedelta(hours=1),
        fecha_hora_fin=now_utc + timedelta(hours=1, minutes=30),
        estado="RESERVADO",
        es_sobreturno=False,
        ciudadano=ciudadano,
        tramite=tramite,
        variantes=[],
    )

    turno_sob_baja = Turno(
        id=uuid.uuid4(),
        ciudadano_id=2,
        tramite_id=10,
        fecha_hora_inicio=now_utc + timedelta(hours=3),
        fecha_hora_fin=now_utc + timedelta(hours=3, minutes=30),
        estado="RESERVADO",
        es_sobreturno=True,
        sobreturno_prioridad="BAJA",
        ciudadano=ciudadano,
        tramite=tramite,
        variantes=[],
        created_at=now_utc,
    )

    turno_sob_alta = Turno(
        id=uuid.uuid4(),
        ciudadano_id=2,
        tramite_id=10,
        fecha_hora_inicio=now_utc + timedelta(hours=3),
        fecha_hora_fin=now_utc + timedelta(hours=3, minutes=30),
        estado="RESERVADO",
        es_sobreturno=True,
        sobreturno_prioridad="ALTA",
        ciudadano=ciudadano,
        tramite=tramite,
        variantes=[],
        created_at=now_utc + timedelta(minutes=5),
    )

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [
        turno_reg_2,
        turno_reg_1,
        turno_sob_baja,
        turno_sob_alta,
    ]
    db.execute.return_value = mock_res

    with patch("app.services.operation_service.decrypt_pii", side_effect=lambda x: "12345678"):
        res = await OperationService.get_cola_dia(db, fecha=date.today())

    assert len(res) == 4
    # Regulares primero ordenados por inicio
    assert res[0].id == turno_reg_1.id
    assert res[1].id == turno_reg_2.id
    # Sobretornos al final ordenados por prioridad ALTA -> BAJA
    assert res[2].id == turno_sob_alta.id
    assert res[3].id == turno_sob_baja.id


@pytest.mark.asyncio
async def test_registrar_resultado_incompleto_requires_comment():
    """Marcar un turno como INCOMPLETO requiere un comentario explicativo obligatorio."""
    db = AsyncMock()
    db.add = MagicMock()
    admin = User(id=1, nombre="Admin", apellido="User", rol=Role(id=2, nombre="ADMINISTRATIVO"))
    ciudadano = User(id=2, nombre="Juan", apellido="Perez", dni_cifrado="cifrado", telefono_cifrado="cifrado")
    tramite = Tramite(id=10, nombre="Trámite test", emite_carnet=False)

    turno = Turno(
        id=uuid.uuid4(),
        ciudadano_id=2,
        tramite_id=10,
        fecha_hora_inicio=datetime.now(timezone.utc),
        fecha_hora_fin=datetime.now(timezone.utc) + timedelta(minutes=30),
        estado="RESERVADO",
        ciudadano=ciudadano,
        tramite=tramite,
        variantes=[],
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = turno
    db.execute.return_value = mock_res

    req_sin_comentario = TurnoResultadoRequest(estado="INCOMPLETO", resultado_comentario="")
    with pytest.raises(HTTPException) as exc_info:
        await OperationService.registrar_resultado_turno(db, turno.id, req_sin_comentario, admin)
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    with patch("app.services.operation_service.decrypt_pii", return_value="12345678"):
        req_con_comentario = TurnoResultadoRequest(
            estado="INCOMPLETO", resultado_comentario="Falta libre de deuda de faltas"
        )
        res = await OperationService.registrar_resultado_turno(db, turno.id, req_con_comentario, admin)
        assert res.estado == "INCOMPLETO"
        assert res.resultado_comentario == "Falta libre de deuda de faltas"


@pytest.mark.asyncio
async def test_registrar_resultado_completo_con_carnet():
    """Marcar COMPLETO para trámite con emite_carnet=True guarda el registro de Carnet."""
    db = AsyncMock()
    db.add = MagicMock()
    admin = User(id=1, nombre="Admin", apellido="User", rol=Role(id=2, nombre="ADMINISTRATIVO"))
    ciudadano = User(id=2, nombre="Maria", apellido="Lopez", dni_cifrado="cifrado", telefono_cifrado="cifrado")
    tramite = Tramite(id=10, nombre="Carnet Conducir", emite_carnet=True)

    turno = Turno(
        id=uuid.uuid4(),
        ciudadano_id=2,
        tramite_id=10,
        fecha_hora_inicio=datetime.now(timezone.utc),
        fecha_hora_fin=datetime.now(timezone.utc) + timedelta(minutes=30),
        estado="RESERVADO",
        ciudadano=ciudadano,
        tramite=tramite,
        variantes=[],
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = turno
    db.execute.return_value = mock_res

    venc_futuro = (date.today() + timedelta(days=365)).isoformat()
    req = TurnoResultadoRequest(
        estado="COMPLETO",
        resultado_comentario="Trámite finalizado con éxito",
        numero_carnet="ARM-2026-99",
        fecha_vencimiento=venc_futuro,
    )

    with patch("app.services.operation_service.decrypt_pii", return_value="12345678"):
        with patch("app.services.operation_service.encrypt_pii", return_value="encrypted_carnet"):
            with patch("app.services.operation_service.hash_dni_hmac", return_value="hmac_carnet"):
                res = await OperationService.registrar_resultado_turno(db, turno.id, req, admin)
                assert res.estado == "COMPLETO"
                assert db.add.called
