from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.validators import (
    normalize_email,
    sanitize_and_validate_dni,
    sanitize_and_validate_phone,
    validate_name,
    validate_password_policy,
)


class CreateAdminRequest(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    apellido: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    dni: str = Field(..., min_length=7, max_length=10)
    telefono: str = Field(..., min_length=6, max_length=20)
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("nombre", "apellido")
    @classmethod
    def validate_names(cls, v: str) -> str:
        return validate_name(v)

    @field_validator("dni")
    @classmethod
    def validate_dni_format(cls, v: str) -> str:
        return sanitize_and_validate_dni(v)

    @field_validator("telefono")
    @classmethod
    def validate_phone_format(cls, v: str) -> str:
        return sanitize_and_validate_phone(v)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: EmailStr) -> str:
        return normalize_email(v)

    @field_validator("password")
    @classmethod
    def validate_password_format(cls, v: str) -> str:
        return validate_password_policy(v)


class UpdateAdminRequest(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=100)
    apellido: str | None = Field(None, min_length=2, max_length=100)
    email: EmailStr | None = None
    telefono: str | None = Field(None, min_length=6, max_length=20)
    password: str | None = Field(None, min_length=8, max_length=100)
    activo: bool | None = None

    @field_validator("nombre", "apellido")
    @classmethod
    def validate_names(cls, v: str | None) -> str | None:
        return validate_name(v) if v is not None else None

    @field_validator("telefono")
    @classmethod
    def validate_phone_format(cls, v: str | None) -> str | None:
        return sanitize_and_validate_phone(v) if v is not None else None

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: EmailStr | None) -> str | None:
        return normalize_email(v) if v is not None else None

    @field_validator("password")
    @classmethod
    def validate_password_format(cls, v: str | None) -> str | None:
        return validate_password_policy(v) if v is not None else None
