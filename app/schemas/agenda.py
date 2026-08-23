from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgendaConfigSaveItem(BaseModel):
    dia_semana: int = Field(..., ge=0, le=6, description="0=Domingo, 1=Lunes, ..., 6=Sábado")
    hora_inicio: str = Field(
        ...,
        pattern=r"^([01]\d|2[0-3]):([0-5]\d)$",
        json_schema_extra={"example": "08:00"},
    )
    hora_fin: str = Field(
        ...,
        pattern=r"^([01]\d|2[0-3]):([0-5]\d)$",
        json_schema_extra={"example": "12:00"},
    )
    capacidad_simultanea: int = Field(..., ge=1, le=50, json_schema_extra={"example": 2})
    activo: bool = Field(True, json_schema_extra={"example": True})

    @model_validator(mode="after")
    def validate_horarios(self) -> "AgendaConfigSaveItem":
        if self.hora_fin <= self.hora_inicio:
            raise ValueError("La hora_fin debe ser estrictamente posterior a la hora_inicio")
        return self


class AgendaConfigResponse(BaseModel):
    id: int
    tramite_id: int
    dia_semana: int
    hora_inicio: str
    hora_fin: str
    capacidad_simultanea: int
    activo: bool

    model_config = ConfigDict(from_attributes=True)
