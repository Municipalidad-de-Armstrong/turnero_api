from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.tramite_documento import TramiteDocumentoResponse
from app.schemas.tramite_enlace import TramiteEnlaceResponse
from app.schemas.variante import VarianteResponse


class TramiteCreateRequest(BaseModel):
    area_id: int
    nombre: str = Field(..., min_length=3, max_length=150)
    descripcion: str | None = Field(None, max_length=1000)
    documentacion_requerida: str = Field(..., min_length=3)
    requerimientos_previos: str | None = Field(None)
    emite_carnet: bool = Field(default=False)
    limite_sobreturnos_diarios: int | None = Field(default=5, ge=0)


class TramiteUpdateRequest(BaseModel):
    nombre: str | None = Field(None, min_length=3, max_length=150)
    descripcion: str | None = Field(None, max_length=1000)
    documentacion_requerida: str | None = Field(None, min_length=3)
    requerimientos_previos: str | None = Field(None)
    emite_carnet: bool | None = Field(None)
    limite_sobreturnos_diarios: int | None = Field(None, ge=0)


class TramiteResponse(BaseModel):
    id: int
    area_id: int
    nombre: str
    descripcion: str | None = None
    documentacion_requerida: str
    requerimientos_previos: str | None = None
    emite_carnet: bool
    limite_sobreturnos_diarios: int | None = 5
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TramiteDetailResponse(TramiteResponse):
    variantes: list[VarianteResponse] = []
    documentos: list[TramiteDocumentoResponse] = []
    enlaces: list[TramiteEnlaceResponse] = []

    model_config = ConfigDict(from_attributes=True)
