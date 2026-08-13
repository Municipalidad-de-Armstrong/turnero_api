"""Create slice 11 configuracion_global table

Revision ID: 008_slice11_configuracion_global
Revises: 007_slice10_notificaciones_table
Create Date: 2026-08-12 12:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = "008_slice11_configuracion_global"
down_revision = "007_slice10_notificaciones_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "configuracion_global",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "anticipacion_cancelacion_horas",
            sa.Integer(),
            nullable=False,
            server_default="24",
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_configuracion_global_id",
        "configuracion_global",
        ["id"],
        unique=False,
    )
    # Sembrar registro por defecto con ID 1
    op.execute(
        "INSERT INTO configuracion_global (id, anticipacion_cancelacion_horas, created_at, updated_at) "
        "VALUES (1, 24, NOW(), NOW()) ON CONFLICT (id) DO NOTHING"
    )


def downgrade() -> None:
    op.drop_index("ix_configuracion_global_id", table_name="configuracion_global")
    op.drop_table("configuracion_global")
