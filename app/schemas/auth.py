from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.validators import (
    normalize_email,
    sanitize_and_validate_dni,
    sanitize_and_validate_phone,
    validate_name,
    validate_password_policy,
)


class UserRegisterRequest(BaseModel):
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


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: EmailStr) -> str:
        return normalize_email(v)


class PasswordRecoveryRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: EmailStr) -> str:
        return normalize_email(v)


class PasswordResetRequest(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password_format(cls, v: str) -> str:
        return validate_password_policy(v)


class UserResponse(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: str
    dni: str
    telefono: str
    rol: str
    activo: bool
    estado: str = "ACTIVE"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdateRequest(BaseModel):
    telefono: str | None = Field(None, min_length=6, max_length=20)
    email: EmailStr | None = None

    @field_validator("telefono")
    @classmethod
    def validate_phone_format(cls, v: str | None) -> str | None:
        return sanitize_and_validate_phone(v) if v is not None else None

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: EmailStr | None) -> str | None:
        return normalize_email(v) if v is not None else None


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password_format(cls, v: str) -> str:
        return validate_password_policy(v)


class UsurpationReportCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    apellido: str = Field(..., min_length=2, max_length=100)
    dni: str = Field(..., min_length=7, max_length=10)
    email_contacto: EmailStr
    telefono: str = Field(..., min_length=6, max_length=20)
    motivo: str = Field(..., min_length=10, max_length=1000)

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

    @field_validator("email_contacto")
    @classmethod
    def validate_email_format(cls, v: EmailStr) -> str:
        return normalize_email(v)


class UsurpationReportResponse(BaseModel):
    id: int
    nombre: str
    apellido: str
    dni_mascarado: str
    email_contacto: str
    telefono_mascarado: str
    motivo: str
    estado: str
    created_at: datetime
    resolved_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UsurpationReportUpdate(BaseModel):
    estado: str = Field(..., pattern="^(PENDIENTE|RESUELTO|RECHAZADO)$")
    comentario_resolucion: str | None = Field(None, max_length=1000)
