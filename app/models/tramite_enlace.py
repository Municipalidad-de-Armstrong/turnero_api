from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tramite import Tramite


class TramiteEnlace(Base):
    __tablename__ = "tramites_enlaces"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tramite_id: Mapped[int] = mapped_column(
        ForeignKey("tramites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    descripcion: Mapped[str] = mapped_column(String(150), nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
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

    tramite: Mapped["Tramite"] = relationship("Tramite", back_populates="enlaces")
