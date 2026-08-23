from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.validators import validate_http_url


class TramiteEnlaceCreateRequest(BaseModel):
    descripcion: str = Field(..., min_length=2, max_length=150)
    url: str = Field(..., min_length=5, max_length=500)

    @field_validator("descripcion")
    @classmethod
    def clean_desc(cls, v: str) -> str:
        clean = v.strip()
        if len(clean) < 2:
            raise ValueError("La descripción debe tener al menos 2 caracteres.")
        return clean

    @field_validator("url")
    @classmethod
    def check_url(cls, v: str) -> str:
        return validate_http_url(v)


class TramiteEnlaceResponse(BaseModel):
    id: int
    tramite_id: int
    descripcion: str
    url: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
