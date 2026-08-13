from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ConfiguracionGlobal(Base):
    __tablename__ = "configuracion_global"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    anticipacion_cancelacion_horas: Mapped[int] = mapped_column(
        Integer, default=24, nullable=False
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
