from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CarnetCreate(BaseModel):
    ciudadano_id: int = Field(..., description="ID del ciudadano titular")
    tramite_id: int = Field(..., description="ID del trámite")
    numero_carnet: str = Field(..., min_length=1, max_length=100, description="Número físico del carnet")
    fecha_emision: date = Field(..., description="Fecha de emisión")
    fecha_vencimiento: date = Field(..., description="Fecha de vencimiento")


class CarnetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ciudadano_id: int
    tramite_id: int
    numero_carnet: str
    fecha_emision: date
    fecha_vencimiento: date
    activo: bool
    created_at: datetime
    updated_at: datetime
