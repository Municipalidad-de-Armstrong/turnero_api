"""Create slice 6 turnos and turnos_variantes tables

Revision ID: 005_slice6_turnos_tables
Revises: 004_slice5_scheduling_agenda
Create Date: 2026-07-27 15:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005_slice6_turnos_tables"
down_revision = "004_slice5_scheduling_agenda"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "turnos",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("ciudadano_id", sa.Integer(), nullable=False),
        sa.Column("tramite_id", sa.Integer(), nullable=False),
        sa.Column("fecha_hora_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_hora_fin", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "estado",
            sa.String(length=50),
            nullable=False,
            server_default="RESERVADO",
        ),
        sa.Column(
            "es_sobreturno",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("sobreturno_prioridad", sa.String(length=20), nullable=True),
        sa.Column("motivo_cancelacion", sa.Text(), nullable=True),
        sa.Column("cancelado_por_id", sa.Integer(), nullable=True),
        sa.Column("resultado_comentario", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ciudadano_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["tramite_id"], ["tramites.id"]),
        sa.ForeignKeyConstraint(["cancelado_por_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_turnos_rango",
        "turnos",
        ["tramite_id", "fecha_hora_inicio", "fecha_hora_fin", "estado"],
        unique=False,
    )
    op.create_index(
        "idx_turnos_ciudadano", "turnos", ["ciudadano_id"], unique=False
    )

    op.create_table(
        "turnos_variantes",
        sa.Column("turno_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("variante_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["turno_id"], ["turnos.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["variante_id"], ["variantes.id"]),
        sa.PrimaryKeyConstraint("turno_id", "variante_id"),
    )


def downgrade() -> None:
    op.drop_table("turnos_variantes")
    op.drop_index("idx_turnos_ciudadano", table_name="turnos")
    op.drop_index("idx_turnos_rango", table_name="turnos")
    op.drop_table("turnos")
