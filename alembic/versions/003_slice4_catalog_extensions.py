"""Create slice 4 catalog extensions (variantes, tramites_documentos, tramites_enlaces)

Revision ID: 003_slice4_catalog_extensions
Revises: 002_catalog_tables
Create Date: 2026-07-23 12:40:00

"""
from alembic import op
import sqlalchemy as sa

revision = '003_slice4_catalog_extensions'
down_revision = '002_catalog_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'variantes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tramite_id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=150), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('duracion_minutos', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('duracion_minutos > 0', name='check_duracion_minutos_positiva'),
        sa.ForeignKeyConstraint(['tramite_id'], ['tramites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_variantes_id'), 'variantes', ['id'], unique=False)
    op.create_index(op.f('ix_variantes_tramite_id'), 'variantes', ['tramite_id'], unique=False)

    op.create_table(
        'tramites_documentos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tramite_id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=150), nullable=False),
        sa.Column('ruta_archivo', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tramite_id'], ['tramites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tramites_documentos_id'), 'tramites_documentos', ['id'], unique=False)
    op.create_index(op.f('ix_tramites_documentos_tramite_id'), 'tramites_documentos', ['tramite_id'], unique=False)

    op.create_table(
        'tramites_enlaces',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tramite_id', sa.Integer(), nullable=False),
        sa.Column('descripcion', sa.String(length=150), nullable=False),
        sa.Column('url', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tramite_id'], ['tramites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tramites_enlaces_id'), 'tramites_enlaces', ['id'], unique=False)
    op.create_index(op.f('ix_tramites_enlaces_tramite_id'), 'tramites_enlaces', ['tramite_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_tramites_enlaces_tramite_id'), table_name='tramites_enlaces')
    op.drop_index(op.f('ix_tramites_enlaces_id'), table_name='tramites_enlaces')
    op.drop_table('tramites_enlaces')

    op.drop_index(op.f('ix_tramites_documentos_tramite_id'), table_name='tramites_documentos')
    op.drop_index(op.f('ix_tramites_documentos_id'), table_name='tramites_documentos')
    op.drop_table('tramites_documentos')

    op.drop_index(op.f('ix_variantes_tramite_id'), table_name='variantes')
    op.drop_index(op.f('ix_variantes_id'), table_name='variantes')
    op.drop_table('variantes')
