from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.fixture(autouse=True)
def _force_production_env(monkeypatch):
    """El health check solo hace ping directo a Redis (vía ``aioredis.from_url``)
    en producción. Para que los patches de ``aioredis.from_url`` funcionen,
    forzamos ``ENVIRONMENT=production`` en toda la suite de health."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")


@pytest.mark.asyncio
async def test_health_check_healthy(client: AsyncClient):
    """Test health check endpoint when all systems are online."""
    # Mock database execute to succeed
    # Mock Redis ping to succeed
    with patch("app.api.v1.health.aioredis.from_url") as mock_redis_from_url:
        mock_redis_client = AsyncMock()
        mock_redis_client.ping.return_value = True
        mock_redis_from_url.return_value = mock_redis_client
        
        # We override the DB execute in conftest, but here we can mock the session
        # inside health endpoint, or since we patch, we mock the execute on DB
        with patch("sqlalchemy.ext.asyncio.AsyncSession.execute") as mock_db_execute:
            mock_db_execute.return_value = AsyncMock()
            
            response = await client.get("/api/v1/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["database"] == "online"
            assert data["redis"] == "online"


@pytest.mark.asyncio
async def test_health_check_unhealthy_db(client: AsyncClient):
    """Test health check endpoint when database is offline."""
    with patch("app.api.v1.health.aioredis.from_url") as mock_redis_from_url:
        mock_redis_client = AsyncMock()
        mock_redis_client.ping.return_value = True
        mock_redis_from_url.return_value = mock_redis_client
        
        with patch("sqlalchemy.ext.asyncio.AsyncSession.execute", side_effect=Exception("DB Connection refused")):
            response = await client.get("/api/v1/health")
            
            assert response.status_code == 503
            data = response.json()["detail"]
            assert data["status"] == "unhealthy"
            assert data["database"] == "offline"
            assert data["redis"] == "online"
            assert "Database error" in data["errors"][0]


@pytest.mark.asyncio
async def test_health_check_unhealthy_redis(client: AsyncClient):
    """Test health check endpoint when Redis is offline."""
    with patch("app.api.v1.health.aioredis.from_url") as mock_redis_from_url:
        mock_redis_client = AsyncMock()
        mock_redis_client.ping.side_effect = Exception("Redis connection timeout")
        mock_redis_from_url.return_value = mock_redis_client
        
        with patch("sqlalchemy.ext.asyncio.AsyncSession.execute") as mock_db_execute:
            mock_db_execute.return_value = AsyncMock()
            
            response = await client.get("/api/v1/health")
            
            assert response.status_code == 503
            data = response.json()["detail"]
            assert data["status"] == "unhealthy"
            assert data["database"] == "online"
            assert data["redis"] == "offline"
            assert "Redis error" in data["errors"][0]
