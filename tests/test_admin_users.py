import uuid

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


@pytest.mark.asyncio
async def test_admin_user_management(
    client: AsyncClient, db_session: AsyncSession
):
    """Test administrative user list, create, update, and soft delete."""
    unique_suffix = str(uuid.uuid4())[:8]
    unique_email = f"testop.{unique_suffix}@armstrong.gov.ar"
    unique_dni = f"35{unique_suffix[:6]}"

    # 1. Login as Admin
    login_resp = await client.post(
        "/api/v1/auth/tokens",
        json={"email": "admin.dev@armstrong.gov.ar", "password": "Admin123!"},
    )
    assert login_resp.status_code == status.HTTP_200_OK

    # 2. List administrative users
    list_resp = await client.get("/api/v1/admin/administrativos")
    assert list_resp.status_code == status.HTTP_200_OK
    initial_count = len(list_resp.json())
    assert initial_count >= 1

    # 3. Create new administrative user
    create_payload = {
        "nombre": "TestOp",
        "apellido": "Nuevo",
        "email": unique_email,
        "dni": unique_dni,
        "telefono": "3471499999",
        "password": "Password123!",
    }
    create_resp = await client.post(
        "/api/v1/admin/administrativos",
        json=create_payload,
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    created_user = create_resp.json()
    new_id = created_user["id"]
    assert created_user["email"] == unique_email

    # 4. Patch/Update administrative user
    update_payload = {
        "nombre": "TestOpActualizado",
        "telefono": "3471500000",
    }
    patch_resp = await client.patch(
        f"/api/v1/admin/administrativos/{new_id}",
        json=update_payload,
    )
    assert patch_resp.status_code == status.HTTP_200_OK
    assert patch_resp.json()["nombre"] == "TestOpActualizado"

    # 5. Delete (deactivate) administrative user
    del_resp = await client.delete(f"/api/v1/admin/administrativos/{new_id}")
    assert del_resp.status_code == status.HTTP_204_NO_CONTENT

    # Verify state in DB
    stmt = select(User).where(User.id == new_id)
    res = await db_session.execute(stmt)
    user_db = res.scalar_one()
    assert user_db.activo is False
    assert user_db.estado == "INACTIVE"
