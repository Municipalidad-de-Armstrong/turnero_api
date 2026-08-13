from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    titulo: str
    mensaje: str
    leida: bool
    created_at: datetime
    updated_at: datetime


class NotificationUpdateRequest(BaseModel):
    leida: bool
