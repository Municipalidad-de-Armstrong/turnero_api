import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.variante import VarianteResponse


class DatosRegistroInmediato(BaseModel):
    dni: str = Field(..., min_length=7, max_length=20, description="DNI del ciudadano")
    email: str = Field(..., description="Email del ciudadano")
    telefono: str = Field(..., description="Teléfono del ciudadano")
    nombre: str = Field(..., min_length=2, max_length=100, description="Nombre")
    apellido: str = Field(..., min_length=2, max_length=100, description="Apellido")


class TurnoCreateRequest(BaseModel):
    tramite_id: int = Field(..., description="ID del trámite")
    variante_ids: List[int] = Field(..., min_length=1, description="Lista de IDs de variantes a agendar")
    fecha_hora_inicio: datetime = Field(..., description="Fecha y hora de inicio deseada en formato UTC / ISO")
    ciudadano_id: Optional[int] = Field(None, description="Opcional. ID de ciudadano si es cargado por administrativo")
    datos_registro_inmediato: Optional[DatosRegistroInmediato] = Field(
        None, description="Opcional. Datos para registrar al ciudadano al vuelo si es cargado por administrativo"
    )


class SobreturnoCreateRequest(BaseModel):
    tramite_id: int = Field(..., description="ID del trámite")
    fecha: str = Field(..., description="Fecha del sobreturno en formato YYYY-MM-DD")
    prioridad: str = Field("MEDIA", description="Prioridad del sobreturno: ALTA, MEDIA, BAJA")
    ciudadano_id: Optional[int] = Field(None, description="ID del ciudadano si ya está registrado")
    datos_registro_inmediato: Optional[DatosRegistroInmediato] = Field(
        None, description="Datos para registrar al ciudadano al vuelo si no existe"
    )
    variante_ids: Optional[List[int]] = Field(None, description="Opcional. Lista de IDs de variantes asociadas")



class TurnoUpdateRequest(BaseModel):
    fecha_hora_inicio: Optional[datetime] = Field(None, description="Nueva fecha/hora para reprogramación")
    variante_ids: Optional[List[int]] = Field(None, description="Nuevas variantes para reprogramación")
    estado: Optional[str] = Field(None, description="Nuevo estado (RESERVADO, COMPLETO, INCOMPLETO, AUSENTE, CANCELADO)")
    motivo_cancelacion: Optional[str] = Field(None, description="Motivo obligatorio si es cancelado por un administrativo")
    resultado_comentario: Optional[str] = Field(None, description="Comentario del administrativo tras la atención")


class TurnoResultadoRequest(BaseModel):
    estado: str = Field(..., description="Nuevo estado del turno: COMPLETO, INCOMPLETO, AUSENTE")
    resultado_comentario: Optional[str] = Field(None, description="Notas del operador. Obligatorio si es INCOMPLETO")
    numero_carnet: Optional[str] = Field(None, description="Número de carnet. Obligatorio si el trámite emite carnet y estado es COMPLETO")
    fecha_vencimiento: Optional[str] = Field(None, description="Fecha de vencimiento en formato YYYY-MM-DD. Obligatorio si emite carnet y COMPLETO")


class TurnoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ciudadano_id: int
    ciudadano_nombre_completo: Optional[str] = None
    ciudadano_dni: Optional[str] = None
    ciudadano_telefono: Optional[str] = None
    tramite_id: int
    tramite_nombre: Optional[str] = None
    emite_carnet: Optional[bool] = None
    fecha_hora_inicio: datetime
    fecha_hora_fin: datetime
    estado: str
    es_sobreturno: bool
    sobreturno_prioridad: Optional[str] = None
    motivo_cancelacion: Optional[str] = None
    cancelado_por_id: Optional[int] = None
    resultado_comentario: Optional[str] = None
    variantes: List[VarianteResponse] = []
    created_at: datetime

