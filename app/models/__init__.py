from app.core.database import Base
from app.models.role import Role
from app.models.user import User
from app.models.usurpation_report import UsurpationReport
from app.models.area import Area
from app.models.tramite import Tramite
from app.models.variante import Variante
from app.models.tramite_documento import TramiteDocumento
from app.models.tramite_enlace import TramiteEnlace
from app.models.agenda_configuracion import AgendaConfiguracion
from app.models.turno import Turno, turno_variante_table
from app.models.carnet import Carnet
from app.models.notificacion import Notificacion

__all__ = [
    "Base",
    "Role",
    "User",
    "UsurpationReport",
    "Area",
    "Tramite",
    "Variante",
    "TramiteDocumento",
    "TramiteEnlace",
    "AgendaConfiguracion",
    "Turno",
    "turno_variante_table",
    "Carnet",
    "Notificacion",
]


