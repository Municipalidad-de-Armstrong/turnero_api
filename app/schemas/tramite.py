from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.variante import VarianteResponse
from app.schemas.tramite_documento import TramiteDocumentoResponse
from app.schemas.tramite_enlace import TramiteEnlaceResponse


class TramiteCreateRequest(BaseModel):
    area_id: int
    nombre: str = Field(..., min_length=3, max_length=150)
    descripcion: Optional[str] = Field(None, max_length=1000)
    documentacion_requerida: str = Field(..., min_length=3)
    requerimientos_previos: Optional[str] = Field(None)
    emite_carnet: bool = Field(default=False)
    limite_sobreturnos_diarios: Optional[int] = Field(default=5, ge=0)


class TramiteUpdateRequest(BaseModel):
    nombre: Optional[str] = Field(None, min_length=3, max_length=150)
    descripcion: Optional[str] = Field(None, max_length=1000)
    documentacion_requerida: Optional[str] = Field(None, min_length=3)
    requerimientos_previos: Optional[str] = Field(None)
    emite_carnet: Optional[bool] = Field(None)
    limite_sobreturnos_diarios: Optional[int] = Field(None, ge=0)


class TramiteResponse(BaseModel):
    id: int
    area_id: int
    nombre: str
    descripcion: Optional[str] = None
    documentacion_requerida: str
    requerimientos_previos: Optional[str] = None
    emite_carnet: bool
    limite_sobreturnos_diarios: Optional[int] = 5
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TramiteDetailResponse(TramiteResponse):
    variantes: List[VarianteResponse] = []
    documentos: List[TramiteDocumentoResponse] = []
    enlaces: List[TramiteEnlaceResponse] = []

    model_config = ConfigDict(from_attributes=True)
