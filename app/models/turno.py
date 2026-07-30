import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

turno_variante_table = Table(
    "turnos_variantes",
    Base.metadata,
    Column(
        "turno_id",
        UUID(as_uuid=True),
        ForeignKey("turnos.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "variante_id",
        Integer,
        ForeignKey("variantes.id"),
        primary_key=True,
    ),
)


class Turno(Base):
    __tablename__ = "turnos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ciudadano_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.id"), nullable=False
    )
    tramite_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tramites.id"), nullable=False
    )
    fecha_hora_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    fecha_hora_fin: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    estado: Mapped[str] = mapped_column(
        String(50), nullable=False, default="RESERVADO"
    )
    es_sobreturno: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    sobreturno_prioridad: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )
    motivo_cancelacion: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    cancelado_por_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("usuarios.id"), nullable=True
    )
    resultado_comentario: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    ciudadano = relationship("User", foreign_keys=[ciudadano_id])
    cancelado_por = relationship("User", foreign_keys=[cancelado_por_id])
    tramite = relationship("Tramite")
    variantes = relationship(
        "Variante", secondary=turno_variante_table, backref="turnos"
    )
