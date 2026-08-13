from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tramite import Tramite


class Variante(Base):
    __tablename__ = "variantes"
    __table_args__ = (
        CheckConstraint("duracion_minutos > 0", name="check_duracion_minutos_positiva"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tramite_id: Mapped[int] = mapped_column(
        ForeignKey("tramites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    duracion_minutos: Mapped[int] = mapped_column(Integer, nullable=False)
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

    tramite: Mapped["Tramite"] = relationship("Tramite", back_populates="variantes")
