from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AreaCreateRequest(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=100)
    descripcion: str | None = Field(None, max_length=500)

    @field_validator("nombre")
    @classmethod
    def clean_name(cls, v: str) -> str:
        clean = v.strip()
        if len(clean) < 3:
            raise ValueError("El nombre debe tener al menos 3 caracteres.")
        return clean


class AreaUpdateRequest(BaseModel):
    nombre: str | None = Field(None, min_length=3, max_length=100)
    descripcion: str | None = Field(None, max_length=500)

    @field_validator("nombre")
    @classmethod
    def clean_name(cls, v: str | None) -> str | None:
        if v is not None:
            clean = v.strip()
            if len(clean) < 3:
                raise ValueError("El nombre debe tener al menos 3 caracteres.")
            return clean
        return None


class AreaResponse(BaseModel):
    id: int
    nombre: str
    descripcion: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
