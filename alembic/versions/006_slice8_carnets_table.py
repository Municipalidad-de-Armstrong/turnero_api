"""Create slice 8 carnets table

Revision ID: 006_slice8_carnets_table
Revises: 005_slice6_turnos_tables
Create Date: 2026-08-03 11:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = "006_slice8_carnets_table"
down_revision = "005_slice6_turnos_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "carnets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ciudadano_id", sa.Integer(), nullable=False),
        sa.Column("tramite_id", sa.Integer(), nullable=False),
        sa.Column(
            "numero_carnet_cifrado", sa.String(length=500), nullable=False
        ),
        sa.Column(
            "numero_carnet_hmac", sa.String(length=64), nullable=False
        ),
        sa.Column("fecha_emision", sa.Date(), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=False),
        sa.Column(
            "activo",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["ciudadano_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["tramite_id"], ["tramites.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_carnets_id", "carnets", ["id"], unique=False
    )
    op.create_index(
        "ix_carnets_numero_carnet_hmac",
        "carnets",
        ["numero_carnet_hmac"],
        unique=True,
    )
    op.create_index(
        "idx_carnets_vencimiento",
        "carnets",
        ["fecha_vencimiento", "activo"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_carnets_vencimiento", table_name="carnets")
    op.drop_index("ix_carnets_numero_carnet_hmac", table_name="carnets")
    op.drop_index("ix_carnets_id", table_name="carnets")
    op.drop_table("carnets")
