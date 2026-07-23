"""Create catalog tables (areas, tramites)

Revision ID: 002_catalog_tables
Revises: 001_initial_auth
Create Date: 2026-07-23 00:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = '002_catalog_tables'
down_revision = '001_initial_auth'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'areas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_areas_id'), 'areas', ['id'], unique=False)
    op.create_index(op.f('ix_areas_nombre'), 'areas', ['nombre'], unique=True)

    op.create_table(
        'tramites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('area_id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=150), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('documentacion_requerida', sa.Text(), nullable=False),
        sa.Column('requerimientos_previos', sa.Text(), nullable=True),
        sa.Column('emite_carnet', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('limite_sobreturnos_diarios', sa.Integer(), nullable=True, server_default=sa.text('5')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['area_id'], ['areas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tramites_id'), 'tramites', ['id'], unique=False)
    op.create_index(op.f('ix_tramites_area_id'), 'tramites', ['area_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_tramites_area_id'), table_name='tramites')
    op.drop_index(op.f('ix_tramites_id'), table_name='tramites')
    op.drop_table('tramites')
    op.drop_index(op.f('ix_areas_nombre'), table_name='areas')
    op.drop_index(op.f('ix_areas_id'), table_name='areas')
    op.drop_table('areas')
