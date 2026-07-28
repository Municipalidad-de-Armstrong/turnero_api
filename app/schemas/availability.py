from datetime import datetime
from pydantic import BaseModel, ConfigDict


class BloqueDisponibilidad(BaseModel):
    fecha_hora_inicio: datetime
    fecha_hora_fin: datetime
    disponible: bool

    model_config = ConfigDict(from_attributes=True)
