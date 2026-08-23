from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VarianteCreateRequest(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=150)
    descripcion: str | None = Field(None, max_length=1000)
    duracion_minutos: int = Field(
        ..., gt=0, le=480, description="Duración en minutos (entre 1 y 480 minutos)"
    )

    @field_validator("nombre")
    @classmethod
    def clean_name(cls, v: str) -> str:
        clean = v.strip()
        if len(clean) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres.")
        return clean


class VarianteUpdateRequest(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=150)
    descripcion: str | None = Field(None, max_length=1000)
    duracion_minutos: int | None = Field(
        None, gt=0, le=480, description="Duración en minutos (entre 1 y 480 minutos)"
    )

    @field_validator("nombre")
    @classmethod
    def clean_name(cls, v: str | None) -> str | None:
        if v is not None:
            clean = v.strip()
            if len(clean) < 2:
                raise ValueError("El nombre debe tener al menos 2 caracteres.")
            return clean
        return None


class VarianteResponse(BaseModel):
    id: int
    tramite_id: int
    nombre: str
    descripcion: str | None = None
    duracion_minutos: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
