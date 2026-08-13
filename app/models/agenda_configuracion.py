from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tramite import Tramite


class AgendaConfiguracion(Base):
    __tablename__ = "agenda_configuracion"
    __table_args__ = (
        UniqueConstraint("tramite_id", "dia_semana", name="uq_agenda_tramite_dia"),
        CheckConstraint("dia_semana >= 0 AND dia_semana <= 6", name="check_dia_semana_valido"),
        CheckConstraint("capacidad_simultanea >= 1", name="check_capacidad_simultanea_positiva"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tramite_id: Mapped[int] = mapped_column(
        ForeignKey("tramites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dia_semana: Mapped[int] = mapped_column(Integer, nullable=False)
    hora_inicio: Mapped[str] = mapped_column(String(5), nullable=False)
    hora_fin: Mapped[str] = mapped_column(String(5), nullable=False)
    capacidad_simultanea: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
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

    tramite: Mapped["Tramite"] = relationship("Tramite", back_populates="agenda_configuraciones")
