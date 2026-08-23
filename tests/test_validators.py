import pytest
from pydantic import ValidationError

from app.core.validators import (
    normalize_email,
    sanitize_and_validate_dni,
    sanitize_and_validate_phone,
    validate_http_url,
    validate_name,
    validate_password_policy,
)
from app.schemas.agenda import AgendaConfigSaveItem
from app.schemas.auth import UserRegisterRequest
from app.schemas.tramite import TramiteCreateRequest
from app.schemas.tramite_enlace import TramiteEnlaceCreateRequest
from app.schemas.variante import VarianteCreateRequest


def test_sanitize_and_validate_dni_success():
    assert sanitize_and_validate_dni("38.123.456") == "38123456"
    assert sanitize_and_validate_dni(" 40 123 456 ") == "40123456"
    assert sanitize_and_validate_dni("1234567") == "1234567"
    assert sanitize_and_validate_dni("1234567890") == "1234567890"


def test_sanitize_and_validate_dni_failure():
    with pytest.raises(ValueError):
        sanitize_and_validate_dni("12345")  # Too short
    with pytest.raises(ValueError):
        sanitize_and_validate_dni("123456789012")  # Too long
    with pytest.raises(ValueError):
        sanitize_and_validate_dni("ABCDEFG")  # No digits


def test_sanitize_and_validate_phone_success():
    assert sanitize_and_validate_phone("3471-555666") == "3471-555666"
    assert sanitize_and_validate_phone("+54 9 3471 55-6677") == "+54 9 3471 55-6677"


def test_sanitize_and_validate_phone_failure():
    with pytest.raises(ValueError):
        sanitize_and_validate_phone("123")  # Too few digits
    with pytest.raises(ValueError):
        sanitize_and_validate_phone("abcdefg")  # Non-phone string


def test_validate_name_success():
    assert validate_name("  María José  ") == "María José"
    assert validate_name("O'Connor") == "O'Connor"
    assert validate_name("Pérez-Gómez") == "Pérez-Gómez"


def test_validate_name_failure():
    with pytest.raises(ValueError):
        validate_name("Juan123")  # Numbers
    with pytest.raises(ValueError):
        validate_name("J")  # Too short
    with pytest.raises(ValueError):
        validate_name("@Admin")  # Special chars


def test_normalize_email():
    assert normalize_email("  JUAN.PEREZ@Example.Com  ") == "juan.perez@example.com"


def test_validate_password_policy():
    assert validate_password_policy("Secret123") == "Secret123"
    with pytest.raises(ValueError):
        validate_password_policy("onlyletters")
    with pytest.raises(ValueError):
        validate_password_policy("12345678")


def test_validate_http_url():
    assert validate_http_url("https://armstrong.gob.ar/tramites") == "https://armstrong.gob.ar/tramites"
    assert validate_http_url("http://example.com") == "http://example.com"
    with pytest.raises(ValueError):
        validate_http_url("ftp://server.com")
    with pytest.raises(ValueError):
        validate_http_url("not a url")


def test_agenda_config_strict_time():
    item = AgendaConfigSaveItem(
        dia_semana=1,
        hora_inicio="08:00",
        hora_fin="12:30",
        capacidad_simultanea=2,
    )
    assert item.hora_inicio == "08:00"

    with pytest.raises(ValidationError):
        AgendaConfigSaveItem(
            dia_semana=1,
            hora_inicio="25:00",  # Invalid hour
            hora_fin="12:00",
            capacidad_simultanea=1,
        )


def test_variante_duracion_bounds():
    v = VarianteCreateRequest(
        nombre="Trámite Rápido",
        duracion_minutos=30,
    )
    assert v.duracion_minutos == 30

    with pytest.raises(ValidationError):
        VarianteCreateRequest(
            nombre="Trámite Infinito",
            duracion_minutos=600,  # Exceeds 480
        )
