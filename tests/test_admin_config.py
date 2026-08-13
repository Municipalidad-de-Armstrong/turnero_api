import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.configuracion_global import ConfiguracionGlobal


@pytest.mark.asyncio
async def test_get_and_patch_global_config_rbac(
    client: AsyncClient, db_session: AsyncSession
):
    """Test global config GET and PATCH endpoints authorization and behavior."""
    # 1. Login as Admin
    login_resp = await client.post(
        "/api/v1/auth/tokens",
        json={"email": "admin.dev@armstrong.gov.ar", "password": "Admin123!"},
    )
    assert login_resp.status_code == status.HTTP_200_OK

    # 2. Get global config as Admin
    get_resp = await client.get("/api/v1/admin/configuracion")
    assert get_resp.status_code == status.HTTP_200_OK
    data = get_resp.json()
    assert "anticipacion_cancelacion_horas" in data
    assert data["anticipacion_cancelacion_horas"] >= 1

    # 3. Patch global config as Admin
    patch_resp = await client.patch(
        "/api/v1/admin/configuracion",
        json={"anticipacion_cancelacion_horas": 48},
    )
    assert patch_resp.status_code == status.HTTP_200_OK
    assert patch_resp.json()["anticipacion_cancelacion_horas"] == 48

    # Verify DB update
    stmt = select(ConfiguracionGlobal).where(ConfiguracionGlobal.id == 1)
    res = await db_session.execute(stmt)
    config = res.scalar_one()
    assert config.anticipacion_cancelacion_horas == 48

    # 4. Login as Operador (Non-admin)
    login_op = await client.post(
        "/api/v1/auth/tokens",
        json={"email": "operador.dev@armstrong.gov.ar", "password": "Operador123!"},
    )
    assert login_op.status_code == status.HTTP_200_OK

    # Attempt PATCH as Operador -> 403 Forbidden
    forbidden_patch = await client.patch(
        "/api/v1/admin/configuracion",
        json={"anticipacion_cancelacion_horas": 12},
    )
    assert forbidden_patch.status_code == status.HTTP_403_FORBIDDEN
