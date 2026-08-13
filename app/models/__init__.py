from app.core.database import Base
from app.models.agenda_configuracion import AgendaConfiguracion
from app.models.area import Area
from app.models.carnet import Carnet
from app.models.configuracion_global import ConfiguracionGlobal
from app.models.notificacion import Notificacion
from app.models.role import Role
from app.models.tramite import Tramite
from app.models.tramite_documento import TramiteDocumento
from app.models.tramite_enlace import TramiteEnlace
from app.models.turno import Turno, turno_variante_table
from app.models.user import User
from app.models.usurpation_report import UsurpationReport
from app.models.variante import Variante

__all__ = [
    "AgendaConfiguracion",
    "Area",
    "Base",
    "Carnet",
    "ConfiguracionGlobal",
    "Notificacion",
    "Role",
    "Tramite",
    "TramiteDocumento",
    "TramiteEnlace",
    "Turno",
    "User",
    "UsurpationReport",
    "Variante",
    "turno_variante_table",
]


