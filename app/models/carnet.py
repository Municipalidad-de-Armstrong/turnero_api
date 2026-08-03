from datetime import date, datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tramite import Tramite
    from app.models.user import User


class Carnet(Base):
    __tablename__ = "carnets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ciudadano_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id"), nullable=False
    )
    tramite_id: Mapped[int] = mapped_column(
        ForeignKey("tramites.id"), nullable=False
    )
    numero_carnet_cifrado: Mapped[str] = mapped_column(
        String(500), nullable=False
    )
    numero_carnet_hmac: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    ciudadano: Mapped["User"] = relationship("User")
    tramite: Mapped["Tramite"] = relationship("Tramite")
