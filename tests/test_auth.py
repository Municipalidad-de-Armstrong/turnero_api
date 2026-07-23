from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from httpx import AsyncClient
from app.models.role import Role
from app.schemas.auth import UserResponse, UsurpationReportResponse


@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient):
    """Test registering a new citizen user successfully."""
    mock_role = Role(id=1, nombre="ciudadano", descripcion="Ciudadano")

    mock_db_result = MagicMock()
    mock_db_result.scalar_one_or_none.side_effect = [None, None, mock_role]

    with patch("app.services.auth_service.AuthService.register_user") as mock_reg:
        mock_reg.return_value = UserResponse(
            id=1,
            nombre="Juan",
            apellido="Pérez",
            email="juan.perez@ejemplo.com",
            dni="XX.XXX.456",
            telefono="XXXX-XX6677",
            rol="ciudadano",
            activo=True,
            estado="ACTIVE",
            created_at=datetime.now(timezone.utc),
        )

        payload = {
            "nombre": "Juan",
            "apellido": "Pérez",
            "email": "juan.perez@ejemplo.com",
            "dni": "38123456",
            "telefono": "3471556677",
            "password": "Password123!",
        }

        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "juan.perez@ejemplo.com"
        assert data["dni"] == "XX.XXX.456"
        assert data["telefono"] == "XXXX-XX6677"
        assert data["estado"] == "ACTIVE"


@pytest.mark.asyncio
async def test_report_usurpation_success(client: AsyncClient):
    """Test reporting a DNI usurpation with complainant details."""
    payload = {
        "nombre": "Juan",
        "apellido": "Real",
        "dni": "38123456",
        "email_contacto": "juan.real@ejemplo.com",
        "telefono": "3471998877",
        "motivo": "Intento registrarme y mi DNI figura en uso por otra persona.",
    }

    with patch("app.api.v1.admin_usurpations.AuthService.create_usurpation_report") as mock_rep:
        mock_rep.return_value = UsurpationReportResponse(
            id=1,
            nombre="Juan",
            apellido="Real",
            dni_mascarado="XX.XXX.456",
            email_contacto="juan.real@ejemplo.com",
            telefono_mascarado="XXXX-XX8877",
            motivo="Intento registrarme y mi DNI figura en uso por otra persona.",
            estado="PENDIENTE",
            created_at=datetime.now(timezone.utc),
        )

        response = await client.post("/api/v1/reportes-usurpacion", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["nombre"] == "Juan"
        assert data["apellido"] == "Real"
        assert data["dni_mascarado"] == "XX.XXX.456"
        assert data["email_contacto"] == "juan.real@ejemplo.com"
        assert data["estado"] == "PENDIENTE"
