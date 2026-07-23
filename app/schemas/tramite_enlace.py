from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class TramiteEnlaceCreateRequest(BaseModel):
    descripcion: str = Field(..., min_length=2, max_length=150)
    url: str = Field(..., min_length=5, max_length=255)


class TramiteEnlaceResponse(BaseModel):
    id: int
    tramite_id: int
    descripcion: str
    url: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
