import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.notification_service import (
    create_in_app_notification,
    get_user_notifications,
    update_notification_read_status,
)
from app.services.pdf_service import generate_turno_planilla_pdf


@pytest.mark.asyncio
async def test_pdf_generation_bytes():
    """Validates that generate_turno_planilla_pdf produces valid PDF header bytes."""
    pdf_data = generate_turno_planilla_pdf(
        turno_id="a8b792ff-4c28-4e3a-939e-49b8ef6c7438",
        ciudadano_nombre="Juan Pérez",
        ciudadano_dni="35.123.456",
        tramite_nombre="Renovación Carnet B1",
        area_nombre="Tránsito y Seguridad Vial",
        variantes_info="Examen Teórico - 30 min",
        fecha_hora_inicio="2026-08-10 08:30",
        fecha_hora_fin="09:00",
        documentacion_requerida="- DNI original\n- Carnet anterior",
        requerimientos_previos="- Abonar Cenat",
    )
    assert pdf_data is not None
    assert len(pdf_data) > 500
    assert pdf_data.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_notification_service_crud(db_session: AsyncSession):
    """Tests notification creation, retrieval, and read status updating."""
    user_id = 1
    n1 = await create_in_app_notification(
        db_session,
        usuario_id=user_id,
        titulo="Turno Confirmado",
        mensaje="Su turno ha sido reservado.",
    )
    assert n1.id is not None
    assert n1.leida is False

    unread_list = await get_user_notifications(db_session, usuario_id=user_id, solo_no_leidas=True)
    assert len(unread_list) >= 1
    assert any(n.id == n1.id for n in unread_list)

    updated = await update_notification_read_status(
        db_session, notificacion_id=n1.id, usuario_id=user_id, leida=True
    )
    assert updated is not None
    assert updated.leida is True

    unread_after = await get_user_notifications(db_session, usuario_id=user_id, solo_no_leidas=True)
    assert not any(n.id == n1.id for n in unread_after)
