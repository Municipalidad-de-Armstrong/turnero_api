from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status
from httpx import AsyncClient

from app.models.user import User
from app.services.auth_service import AuthService
from app.services.auth_token_service import PASSWORD_RESET_KEY_PREFIX


def _build_user_mock(activo: bool = True, estado: str = "ACTIVE") -> MagicMock:
    user = MagicMock(spec=User)
    user.id = 42
    user.email = "ciudadano@ejemplo.com"
    user.activo = activo
    user.estado = estado
    user.password_hash = "old_hash"
    return user


# ---------------- create_password_reset_token ----------------

@pytest.mark.asyncio
async def test_create_reset_token_persists_in_redis():
    db = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = _build_user_mock()
    db.execute.return_value = res

    redis = AsyncMock()
    service = AuthService(db, redis)

    with patch.object(AuthService, "_send_reset_link") as mock_send:
        await service.create_password_reset_token("ciudadano@ejemplo.com")

    # Debe haber persistido exactamente un token con TTL configurado.
    assert redis.setex.await_count == 1
    args, _kwargs = redis.setex.call_args
    key = args[0]
    assert key.startswith(f"{PASSWORD_RESET_KEY_PREFIX}:")
    # El segundo argumento posicional de setex es el TTL en segundos (15 min).
    assert args[1] == 15 * 60
    assert args[2] == "42"
    mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_create_reset_token_unknown_user_does_not_emit():
    """Anti-enumeración: usuario inexistente no genera token ni envío."""
    db = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = None
    db.execute.return_value = res

    redis = AsyncMock()
    service = AuthService(db, redis)

    await service.create_password_reset_token("noexiste@ejemplo.com")

    redis.setex.assert_not_called()


@pytest.mark.asyncio
async def test_create_reset_token_inactive_user_does_not_emit():
    db = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = _build_user_mock(activo=False)
    db.execute.return_value = res

    redis = AsyncMock()
    service = AuthService(db, redis)

    await service.create_password_reset_token("ciudadano@ejemplo.com")

    redis.setex.assert_not_called()


@pytest.mark.asyncio
async def test_create_reset_token_no_redis_is_silent():
    """Sin Redis disponible, no rompe (preserva respuesta anti-enumeración)."""
    db = AsyncMock()
    service = AuthService(db, None)
    # No debe lanzar excepción.
    await service.create_password_reset_token("ciudadano@ejemplo.com")


# ---------------- apply_password_reset ----------------

@pytest.mark.asyncio
async def test_apply_reset_updates_password_and_consumes_token():
    user = _build_user_mock()
    db = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = user
    db.execute.return_value = res

    redis = AsyncMock()
    redis.get.return_value = "42"

    service = AuthService(db, redis)
    await service.apply_password_reset("valid-token-123", "NuevaClave1")

    # La contraseña se actualizó (no es el hash viejo).
    assert user.password_hash != "old_hash"
    db.commit.assert_awaited_once()
    # Single-use: el token se consume.
    redis.delete.assert_awaited_once_with(f"{PASSWORD_RESET_KEY_PREFIX}:valid-token-123")


@pytest.mark.asyncio
async def test_apply_reset_invalid_token_raises_400():
    db = AsyncMock()
    redis = AsyncMock()
    redis.get.return_value = None  # token expirado o inexistente

    service = AuthService(db, redis)
    with pytest.raises(HTTPException) as exc:
        await service.apply_password_reset("bad-token-xxxxx", "NuevaClave1")
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_apply_reset_no_redis_raises_503():
    db = AsyncMock()
    service = AuthService(db, None)
    with pytest.raises(HTTPException) as exc:
        await service.apply_password_reset("some-token-yyy", "NuevaClave1")
    assert exc.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.asyncio
async def test_apply_reset_corrupted_payload_raises_400():
    db = AsyncMock()
    redis = AsyncMock()
    redis.get.return_value = "not-an-int"

    service = AuthService(db, redis)
    with pytest.raises(HTTPException) as exc:
        await service.apply_password_reset("valid-token-123", "NuevaClave1")
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


# ---------------- Endpoints E2E ----------------

@pytest.mark.asyncio
async def test_endpoint_recovery_always_returns_200(client: AsyncClient):
    """El endpoint público siempre responde 200 (anti-enumeración) incluso si el
    servicio no genera token (usuario inexistente, Redis caído)."""
    with patch("app.api.v1.auth.AuthService.create_password_reset_token") as mock_create:
        mock_create.return_value = None
        res = await client.post(
            "/api/v1/auth/password-recovery-tokens",
            json={"email": "cualquiera@ejemplo.com"},
        )
    assert res.status_code == 200
    assert "enviado" in res.json()["detail"].lower()
    mock_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_endpoint_reset_success(client: AsyncClient):
    with patch("app.api.v1.auth.AuthService.apply_password_reset") as mock_apply:
        mock_apply.return_value = None
        res = await client.post(
            "/api/v1/auth/password-resets",
            json={"token": "valid-token-123", "new_password": "NuevaClave1"},
        )
    assert res.status_code == 200
    assert "actualizada" in res.json()["detail"].lower()
    mock_apply.assert_awaited_once_with("valid-token-123", "NuevaClave1")


@pytest.mark.asyncio
async def test_endpoint_reset_weak_password_rejected(client: AsyncClient):
    """La validación de política de contraseña (letra + número) aplica a nivel schema."""
    res = await client.post(
        "/api/v1/auth/password-resets",
        json={"token": "valid-token-123", "new_password": "sololetras"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_endpoint_reset_invalid_token_passes_through_400(client: AsyncClient):
    with patch("app.api.v1.auth.AuthService.apply_password_reset") as mock_apply:
        mock_apply.side_effect = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido o expirado."
        )
        res = await client.post(
            "/api/v1/auth/password-resets",
            json={"token": "expired-token-xx", "new_password": "NuevaClave1"},
        )
    assert res.status_code == 400
