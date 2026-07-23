from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class VarianteCreateRequest(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=150)
    descripcion: Optional[str] = Field(None, max_length=1000)
    duracion_minutos: int = Field(..., gt=0, description="Duración en minutos (debe ser mayor a 0)")


class VarianteUpdateRequest(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=150)
    descripcion: Optional[str] = Field(None, max_length=1000)
    duracion_minutos: Optional[int] = Field(None, gt=0, description="Duración en minutos (debe ser mayor a 0)")


class VarianteResponse(BaseModel):
    id: int
    tramite_id: int
    nombre: str
    descripcion: Optional[str] = None
    duracion_minutos: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
