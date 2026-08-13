
from pydantic import BaseModel, ConfigDict, Field


class GlobalConfigResponse(BaseModel):
    anticipacion_cancelacion_horas: int = Field(
        ...,
        description="Tiempo mínimo en horas antes del turno para que un ciudadano pueda cancelarlo o reprogramarlo.",
        json_schema_extra={"example": 24},
    )

    model_config = ConfigDict(from_attributes=True)


class GlobalConfigUpdateRequest(BaseModel):
    anticipacion_cancelacion_horas: int | None = Field(
        None,
        ge=1,
        description="Nuevo tiempo mínimo en horas de anticipación.",
        json_schema_extra={"example": 24},
    )
