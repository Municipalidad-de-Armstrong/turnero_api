from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AreaCreateRequest(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=100)
    descripcion: str | None = Field(None, max_length=500)


class AreaUpdateRequest(BaseModel):
    nombre: str | None = Field(None, min_length=3, max_length=100)
    descripcion: str | None = Field(None, max_length=500)


class AreaResponse(BaseModel):
    id: int
    nombre: str
    descripcion: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
