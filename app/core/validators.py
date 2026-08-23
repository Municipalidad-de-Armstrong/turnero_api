import re
from pydantic import EmailStr

NAME_REGEX = re.compile(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s'-]{2,100}$")
DNI_REGEX = re.compile(r"^\d{7,10}$")
PHONE_FORMAT_REGEX = re.compile(r"^(\+?[0-9\s\-()]{6,20})$")
URL_REGEX = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)


def sanitize_and_validate_dni(v: str) -> str:
    if not v:
        raise ValueError("El DNI es obligatorio.")
    clean = re.sub(r"\D", "", str(v).strip())
    if not DNI_REGEX.match(clean):
        raise ValueError("El DNI debe contener entre 7 y 10 dígitos numéricos.")
    return clean


def sanitize_and_validate_phone(v: str) -> str:
    if not v:
        raise ValueError("El teléfono es obligatorio.")
    clean = str(v).strip()
    digits = re.sub(r"\D", "", clean)
    if not (6 <= len(digits) <= 15) or not PHONE_FORMAT_REGEX.match(clean):
        raise ValueError(
            "El teléfono debe contener entre 6 y 15 dígitos numéricos y un formato válido."
        )
    return clean


def validate_name(v: str) -> str:
    if not v:
        raise ValueError("El campo es obligatorio.")
    clean = " ".join(str(v).strip().split())
    if not NAME_REGEX.match(clean):
        raise ValueError(
            "El nombre o apellido solo puede contener letras, espacios y guiones (entre 2 y 100 caracteres)."
        )
    return clean


def normalize_email(v: str | EmailStr) -> str:
    if not v:
        raise ValueError("El correo electrónico es obligatorio.")
    return str(v).strip().lower()


def validate_password_policy(v: str) -> str:
    if not v or len(v) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    if not re.search(r"[A-Za-z]", v) or not re.search(r"[0-9]", v):
        raise ValueError("La contraseña debe incluir al menos una letra y un número.")
    return v


def validate_http_url(v: str) -> str:
    clean = str(v).strip()
    if not URL_REGEX.match(clean):
        raise ValueError("La URL debe ser un enlace válido que comience con http:// o https://.")
    return clean
