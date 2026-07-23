from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class AreaCreateRequest(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)


class AreaUpdateRequest(BaseModel):
    nombre: Optional[str] = Field(None, min_length=3, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)


class AreaResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
