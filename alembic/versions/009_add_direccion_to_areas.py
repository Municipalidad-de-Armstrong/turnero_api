"""Add direccion to areas table

Revision ID: 009_add_direccion_to_areas
Revises: 008_slice11_configuracion_global
Create Date: 2026-08-25 19:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = "009_add_direccion_to_areas"
down_revision = "008_slice11_configuracion_global"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("areas", sa.Column("direccion", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("areas", "direccion")
