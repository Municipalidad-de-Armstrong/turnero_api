from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import settings
from app.core.seeds import seed_initial_data
from app.core.seeds.agenda_seed import seed_agenda_configs
from app.core.seeds.catalog_seed import seed_catalog
from app.core.seeds.turnos_seed import seed_turnos_and_reports
from app.core.seeds.users_seed import seed_roles_and_users
from app.models.role import Role
from app.models.tramite import Tramite
from app.models.user import User


def _create_mock_session() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_res
    return db


@pytest.mark.asyncio
async def test_seed_roles_and_users():
    """Test seeding roles and dev user accounts."""
    db = _create_mock_session()

    users = await seed_roles_and_users(db)

    assert "admin.dev@armstrong.gov.ar" in users
    assert "operador.dev@armstrong.gov.ar" in users
    assert "operador2.dev@armstrong.gov.ar" in users
    assert "ciudadano.dev@armstrong.gov.ar" in users
    assert "ciudadano2.dev@armstrong.gov.ar" in users
    assert "ciudadano3.dev@armstrong.gov.ar" in users
    assert db.commit.called


@pytest.mark.asyncio
async def test_seed_catalog():
    """Test seeding areas, tramites, variantes, docs and links."""
    db = _create_mock_session()

    catalog = await seed_catalog(db)

    assert "Licencia de Conducir" in catalog
    assert "Libre Deuda de Infracciones" in catalog
    assert "Permiso de Edificación y Obra" in catalog
    assert "Habilitación Comercial e Industrial" in catalog
    assert db.commit.called


@pytest.mark.asyncio
async def test_seed_agenda_configs():
    """Test seeding distinct agenda configurations."""
    db = _create_mock_session()

    fake_tramite = Tramite(id=10, nombre="Licencia de Conducir")
    catalog = {
        "Licencia de Conducir": {"tramite": fake_tramite, "variantes": {}},
    }

    await seed_agenda_configs(db, catalog)
    assert db.add.called
    assert db.commit.called


@pytest.mark.asyncio
async def test_seed_turnos_and_reports():
    """Test seeding test turnos and usurpation reports."""
    db = _create_mock_session()

    users = {
        "ciudadano.dev@armstrong.gov.ar": User(id=1, email="ciudadano.dev@armstrong.gov.ar"),
        "ciudadano2.dev@armstrong.gov.ar": User(id=2, email="ciudadano2.dev@armstrong.gov.ar"),
        "ciudadano3.dev@armstrong.gov.ar": User(id=3, email="ciudadano3.dev@armstrong.gov.ar"),
    }
    catalog = {
        "Licencia de Conducir": {
            "tramite": Tramite(id=100, nombre="Licencia de Conducir"),
            "variantes": {},
        },
        "Libre Deuda de Infracciones": {
            "tramite": Tramite(id=101, nombre="Libre Deuda de Infracciones"),
            "variantes": {},
        },
        "Permiso de Edificación y Obra": {
            "tramite": Tramite(id=102, nombre="Permiso de Edificación y Obra"),
            "variantes": {},
        },
        "Habilitación Comercial e Industrial": {
            "tramite": Tramite(id=103, nombre="Habilitación Comercial e Industrial"),
            "variantes": {},
        },
    }

    await seed_turnos_and_reports(db, users, catalog)
    assert db.add.called
    assert db.commit.called


@pytest.mark.asyncio
async def test_seed_initial_data_orchestrator(monkeypatch):
    """Test orchestrator running in development vs production environment."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    db = _create_mock_session()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = Role(id=1, nombre="ciudadano")
    db.execute.return_value = mock_res

    await seed_initial_data(db)
    assert db.commit.called

    # Production mode check
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    db_prod = _create_mock_session()
    mock_res_prod = MagicMock()
    mock_res_prod.scalar_one_or_none.return_value = Role(id=1, nombre="ciudadano")
    db_prod.execute.return_value = mock_res_prod

    await seed_initial_data(db_prod)
    assert db_prod.commit.called
