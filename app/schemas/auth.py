import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRegisterRequest(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    apellido: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    dni: str = Field(..., min_length=7, max_length=12)
    telefono: str = Field(..., min_length=6, max_length=20)
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password_policy(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v) or not re.search(r"[0-9]", v):
            raise ValueError("La contraseña debe incluir al menos una letra y un número.")
        return v


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordRecoveryRequest(BaseModel):
    email: EmailStr


class PasswordResetRequest(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password_policy(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v) or not re.search(r"[0-9]", v):
            raise ValueError("La contraseña debe incluir al menos una letra y un número.")
        return v


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
    telefono: Optional[str] = Field(None, min_length=6, max_length=20)
    email: Optional[EmailStr] = None


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password_policy(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v) or not re.search(r"[0-9]", v):
            raise ValueError("La contraseña debe incluir al menos una letra y un número.")
        return v



class UsurpationReportCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    apellido: str = Field(..., min_length=2, max_length=100)
    dni: str = Field(..., min_length=7, max_length=12)
    email_contacto: EmailStr
    telefono: str = Field(..., min_length=6, max_length=20)
    motivo: str = Field(..., min_length=10, max_length=1000)


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
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UsurpationReportUpdate(BaseModel):
    estado: str = Field(..., pattern="^(PENDIENTE|RESUELTO|RECHAZADO)$")
    comentario_resolucion: Optional[str] = Field(None, max_length=1000)
