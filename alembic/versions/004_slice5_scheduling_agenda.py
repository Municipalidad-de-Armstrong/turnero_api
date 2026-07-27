"""Create slice 5 scheduling agenda table (agenda_configuracion)

Revision ID: 004_slice5_scheduling_agenda
Revises: 003_slice4_catalog_extensions
Create Date: 2026-07-27 10:40:00

"""
from alembic import op
import sqlalchemy as sa

revision = '004_slice5_scheduling_agenda'
down_revision = '003_slice4_catalog_extensions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'agenda_configuracion',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tramite_id', sa.Integer(), nullable=False),
        sa.Column('dia_semana', sa.Integer(), nullable=False),
        sa.Column('hora_inicio', sa.String(length=5), nullable=False),
        sa.Column('hora_fin', sa.String(length=5), nullable=False),
        sa.Column('capacidad_simultanea', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('dia_semana >= 0 AND dia_semana <= 6', name='check_dia_semana_valido'),
        sa.CheckConstraint('capacidad_simultanea >= 1', name='check_capacidad_simultanea_positiva'),
        sa.ForeignKeyConstraint(['tramite_id'], ['tramites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tramite_id', 'dia_semana', name='uq_agenda_tramite_dia')
    )
    op.create_index(op.f('ix_agenda_configuracion_id'), 'agenda_configuracion', ['id'], unique=False)
    op.create_index(op.f('ix_agenda_configuracion_tramite_id'), 'agenda_configuracion', ['tramite_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_agenda_configuracion_tramite_id'), table_name='agenda_configuracion')
    op.drop_index(op.f('ix_agenda_configuracion_id'), table_name='agenda_configuracion')
    op.drop_table('agenda_configuracion')
