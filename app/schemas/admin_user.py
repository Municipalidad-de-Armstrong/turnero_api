import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class CreateAdminRequest(BaseModel):
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
            raise ValueError(
                "La contraseña debe incluir al menos una letra y un número."
            )
        return v


class UpdateAdminRequest(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=100)
    apellido: str | None = Field(None, min_length=2, max_length=100)
    email: EmailStr | None = None
    telefono: str | None = Field(None, min_length=6, max_length=20)
    password: str | None = Field(None, min_length=8, max_length=100)
    activo: bool | None = None

    @field_validator("password")
    @classmethod
    def validate_password_policy(cls, v: str | None) -> str | None:
        if v is not None and (not re.search(r"[A-Za-z]", v) or not re.search(r"[0-9]", v)):
            raise ValueError(
                "La contraseña debe incluir al menos una letra y un número."
            )
        return v
