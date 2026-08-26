import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.validators import (
    normalize_email,
    sanitize_and_validate_dni,
    sanitize_and_validate_phone,
    validate_name,
)
from app.schemas.variante import VarianteResponse


class DatosRegistroInmediato(BaseModel):
    dni: str = Field(..., min_length=7, max_length=10, description="DNI del ciudadano")
    email: EmailStr = Field(..., description="Email del ciudadano")
    telefono: str = Field(..., min_length=6, max_length=20, description="Teléfono del ciudadano")
    nombre: str = Field(..., min_length=2, max_length=100, description="Nombre")
    apellido: str = Field(..., min_length=2, max_length=100, description="Apellido")

    @field_validator("nombre", "apellido")
    @classmethod
    def validate_names(cls, v: str) -> str:
        return validate_name(v)

    @field_validator("dni")
    @classmethod
    def validate_dni_format(cls, v: str) -> str:
        return sanitize_and_validate_dni(v)

    @field_validator("telefono")
    @classmethod
    def validate_phone_format(cls, v: str) -> str:
        return sanitize_and_validate_phone(v)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: EmailStr) -> str:
        return normalize_email(v)


class TurnoCreateRequest(BaseModel):
    tramite_id: int = Field(..., description="ID del trámite")
    variante_ids: list[int] = Field(..., min_length=1, description="Lista de IDs de variantes a agendar")
    fecha_hora_inicio: datetime = Field(..., description="Fecha y hora de inicio deseada en formato UTC / ISO")
    ciudadano_id: int | None = Field(None, description="Opcional. ID de ciudadano si es cargado por administrativo")
    datos_registro_inmediato: DatosRegistroInmediato | None = Field(
        None, description="Opcional. Datos para registrar al ciudadano al vuelo si es cargado por administrativo"
    )


class SobreturnoCreateRequest(BaseModel):
    tramite_id: int = Field(..., description="ID del trámite")
    fecha: date = Field(..., description="Fecha del sobreturno en formato YYYY-MM-DD")
    prioridad: str = Field("MEDIA", pattern="^(ALTA|MEDIA|BAJA)$", description="Prioridad del sobreturno: ALTA, MEDIA, BAJA")
    ciudadano_id: int | None = Field(None, description="ID del ciudadano si ya está registrado")
    datos_registro_inmediato: DatosRegistroInmediato | None = Field(
        None, description="Datos para registrar al ciudadano al vuelo si no existe"
    )
    variante_ids: list[int] | None = Field(None, description="Opcional. Lista de IDs de variantes asociadas")


class TurnoUpdateRequest(BaseModel):
    fecha_hora_inicio: datetime | None = Field(None, description="Nueva fecha/hora para reprogramación")
    variante_ids: list[int] | None = Field(None, description="Nuevas variantes para reprogramación")
    estado: str | None = Field(None, pattern="^(RESERVADO|COMPLETO|INCOMPLETO|AUSENTE|CANCELADO)$", description="Nuevo estado")
    motivo_cancelacion: str | None = Field(None, description="Motivo de cancelación (opcional)")
    resultado_comentario: str | None = Field(None, description="Comentario del administrativo tras la atención")


class TurnoResultadoRequest(BaseModel):
    estado: str = Field(..., pattern="^(COMPLETO|INCOMPLETO|AUSENTE)$", description="Nuevo estado del turno: COMPLETO, INCOMPLETO, AUSENTE")
    resultado_comentario: str | None = Field(None, description="Notas del operador. Obligatorio si es INCOMPLETO")
    numero_carnet: str | None = Field(None, description="Número de carnet. Obligatorio si el trámite emite carnet y estado es COMPLETO")
    fecha_vencimiento: date | None = Field(None, description="Fecha de vencimiento en formato YYYY-MM-DD. Obligatorio si emite carnet y COMPLETO")

    @field_validator("numero_carnet")
    @classmethod
    def clean_carnet(cls, v: str | None) -> str | None:
        return v.strip() if v is not None else None


class TurnoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ciudadano_id: int
    ciudadano_nombre_completo: str | None = None
    ciudadano_dni: str | None = None
    ciudadano_telefono: str | None = None
    tramite_id: int
    tramite_nombre: str | None = None
    area_id: int | None = None
    area_nombre: str | None = None
    area_direccion: str | None = None
    emite_carnet: bool | None = None
    fecha_hora_inicio: datetime
    fecha_hora_fin: datetime
    estado: str
    es_sobreturno: bool
    sobreturno_prioridad: str | None = None
    motivo_cancelacion: str | None = None
    cancelado_por_id: int | None = None
    resultado_comentario: str | None = None
    variantes: list[VarianteResponse] = []
    created_at: datetime

