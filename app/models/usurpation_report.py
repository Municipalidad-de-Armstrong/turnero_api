from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UsurpationReport(Base):
    __tablename__ = "reportes_usurpacion_dni"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, server_default="")
    apellido: Mapped[str] = mapped_column(String(100), nullable=False, server_default="")
    dni_hmac: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    dni_cifrado: Mapped[str] = mapped_column(String(500), nullable=False)
    email_contacto: Mapped[str] = mapped_column(String(150), nullable=False)
    telefono_cifrado: Mapped[str] = mapped_column(String(500), nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
