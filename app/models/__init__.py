from app.core.database import Base
from app.models.role import Role
from app.models.user import User
from app.models.usurpation_report import UsurpationReport
from app.models.area import Area
from app.models.tramite import Tramite

__all__ = ["Base", "Role", "User", "UsurpationReport", "Area", "Tramite"]
