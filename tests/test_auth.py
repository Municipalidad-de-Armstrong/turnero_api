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
            dni="38123456",
            telefono="3471556677",
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
        assert data["dni"] == "38123456"
        assert data["telefono"] == "3471556677"
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


@pytest.mark.asyncio
async def test_change_my_password_unauthorized(client: AsyncClient):
    """Test changing password fails when not authenticated."""
    response = await client.post(
        "/api/v1/usuarios/me/password",
        json={"current_password": "OldPass123", "new_password": "NewPass123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_user_profile_unauthorized(client: AsyncClient):
    """Test updating profile fails when not authenticated."""
    response = await client.patch(
        "/api/v1/usuarios/me",
        json={"telefono": "3471556677"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_change_my_password_validation_error(client: AsyncClient):
    """Test password change enforces password policy (at least 8 chars, 1 letter, 1 number)."""
    from app.api.deps import get_current_user
    from app.main import app
    from app.models.user import User

    mock_user = User(id=1, email="c@test.com", password_hash="hash")
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        response = await client.post(
            "/api/v1/usuarios/me/password",
            json={"current_password": "OldPass123", "new_password": "short"},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)



