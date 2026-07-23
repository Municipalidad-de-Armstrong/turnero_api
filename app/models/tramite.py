from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.area import Area


class Tramite(Base):
    __tablename__ = "tramites"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    area_id: Mapped[int] = mapped_column(ForeignKey("areas.id"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    documentacion_requerida: Mapped[str] = mapped_column(Text, nullable=False)
    requerimientos_previos: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emite_carnet: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    limite_sobreturnos_diarios: Mapped[Optional[int]] = mapped_column(
        Integer, default=5, nullable=True
    )
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

    area: Mapped["Area"] = relationship("Area", back_populates="tramites")
