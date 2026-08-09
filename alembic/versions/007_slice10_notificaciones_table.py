"""Create slice 10 notificaciones table

Revision ID: 007_slice10_notificaciones_table
Revises: 006_slice8_carnets_table
Create Date: 2026-08-07 12:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = "007_slice10_notificaciones_table"
down_revision = "006_slice8_carnets_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notificaciones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=150), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("leida", sa.Boolean(), nullable=False, server_default="false"),
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
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuarios.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notificaciones_id", "notificaciones", ["id"], unique=False
    )
    op.create_index(
        "ix_notificaciones_usuario_id",
        "notificaciones",
        ["usuario_id"],
        unique=False,
    )
    op.create_index(
        "idx_notificaciones_usuario_leida",
        "notificaciones",
        ["usuario_id", "leida"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_notificaciones_usuario_leida", table_name="notificaciones")
    op.drop_index("ix_notificaciones_usuario_id", table_name="notificaciones")
    op.drop_index("ix_notificaciones_id", table_name="notificaciones")
    op.drop_table("notificaciones")
