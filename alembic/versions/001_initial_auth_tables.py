"""Initial auth tables (roles, usuarios, reportes_usurpacion_dni)

Revision ID: 001_initial_auth
Revises:
Create Date: 2026-07-21 10:30:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial_auth'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=50), nullable=False),
        sa.Column('descripcion', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_roles_id'), 'roles', ['id'], unique=False)
    op.create_index(op.f('ix_roles_nombre'), 'roles', ['nombre'], unique=True)

    # Insert default roles
    op.execute(
        "INSERT INTO roles (id, nombre, descripcion) VALUES "
        "(1, 'ciudadano', 'Ciudadano solicitante de turnos'), "
        "(2, 'administrativo', 'Personal administrativo de atención'), "
        "(3, 'administrador', 'Administrador general del sistema')"
    )

    # Create usuarios table
    op.create_table(
        'usuarios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('apellido', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=150), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('dni_cifrado', sa.String(length=500), nullable=False),
        sa.Column('dni_hmac', sa.String(length=64), nullable=False),
        sa.Column('telefono_cifrado', sa.String(length=500), nullable=False),
        sa.Column('rol_id', sa.Integer(), nullable=False),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('estado', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['rol_id'], ['roles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_usuarios_email'), 'usuarios', ['email'], unique=True)
    op.create_index(op.f('ix_usuarios_dni_hmac'), 'usuarios', ['dni_hmac'], unique=True)
    op.create_index(op.f('ix_usuarios_id'), 'usuarios', ['id'], unique=False)

    # Create reportes_usurpacion_dni table
    op.create_table(
        'reportes_usurpacion_dni',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('apellido', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('dni_hmac', sa.String(length=64), nullable=False),
        sa.Column('dni_cifrado', sa.String(length=500), nullable=False),
        sa.Column('email_contacto', sa.String(length=150), nullable=False),
        sa.Column('telefono_cifrado', sa.String(length=500), nullable=False),
        sa.Column('motivo', sa.Text(), nullable=False),
        sa.Column('estado', sa.String(length=20), nullable=False, server_default='PENDIENTE'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reportes_usurpacion_dni_dni_hmac'), 'reportes_usurpacion_dni', ['dni_hmac'], unique=False)
    op.create_index(op.f('ix_reportes_usurpacion_dni_id'), 'reportes_usurpacion_dni', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_reportes_usurpacion_dni_id'), table_name='reportes_usurpacion_dni')
    op.drop_index(op.f('ix_reportes_usurpacion_dni_dni_hmac'), table_name='reportes_usurpacion_dni')
    op.drop_table('reportes_usurpacion_dni')
    op.drop_index(op.f('ix_usuarios_id'), table_name='usuarios')
    op.drop_index(op.f('ix_usuarios_dni_hmac'), table_name='usuarios')
    op.drop_index(op.f('ix_usuarios_email'), table_name='usuarios')
    op.drop_table('usuarios')
    op.drop_index(op.f('ix_roles_nombre'), table_name='roles')
    op.drop_index(op.f('ix_roles_id'), table_name='roles')
    op.drop_table('roles')
