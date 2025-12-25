"""Add walk scan tables (bins, captures, gps_samples)

Revision ID: 7c5f3f2b2c0b
Revises: 9626bc482653
Create Date: 2025-12-23 22:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c5f3f2b2c0b'
down_revision: Union[str, Sequence[str], None] = '9626bc482653'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'bins',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('bin_key', sa.String(length=64), nullable=False),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lng', sa.Float(), nullable=True),
        sa.Column('accuracy', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_status', sa.Enum('EMPTY', 'HALF', 'FULL', 'NO_BIN_DETECTED', name='filllevelenum'), nullable=True),
        sa.Column('last_conf', sa.Float(), nullable=True),
        sa.Column('capture_count', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bins_bin_key'), 'bins', ['bin_key'], unique=True)
    op.create_index(op.f('ix_bins_created_at'), 'bins', ['created_at'], unique=False)
    op.create_index(op.f('ix_bins_updated_at'), 'bins', ['updated_at'], unique=False)

    op.create_table(
        'captures',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('bin_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('image_path', sa.String(length=512), nullable=False),
        sa.Column('thumb_path', sa.String(length=512), nullable=True),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lng', sa.Float(), nullable=True),
        sa.Column('accuracy', sa.Float(), nullable=True),
        sa.Column('status', sa.Enum('EMPTY', 'HALF', 'FULL', 'NO_BIN_DETECTED', name='filllevelenum'), nullable=False),
        sa.Column('conf', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('extra_json', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['bin_id'], ['bins.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_captures_bin_id'), 'captures', ['bin_id'], unique=False)
    op.create_index(op.f('ix_captures_session_id'), 'captures', ['session_id'], unique=False)
    op.create_index(op.f('ix_captures_created_at'), 'captures', ['created_at'], unique=False)

    op.create_table(
        'gps_samples',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('device_id', sa.String(length=64), nullable=False),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lng', sa.Float(), nullable=False),
        sa.Column('accuracy', sa.Float(), nullable=False),
        sa.Column('heading', sa.Float(), nullable=True),
        sa.Column('speed', sa.Float(), nullable=True),
        sa.Column('ts_client', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_gps_samples_session_id'), 'gps_samples', ['session_id'], unique=False)
    op.create_index(op.f('ix_gps_samples_device_id'), 'gps_samples', ['device_id'], unique=False)
    op.create_index(op.f('ix_gps_samples_created_at'), 'gps_samples', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_gps_samples_created_at'), table_name='gps_samples')
    op.drop_index(op.f('ix_gps_samples_device_id'), table_name='gps_samples')
    op.drop_index(op.f('ix_gps_samples_session_id'), table_name='gps_samples')
    op.drop_table('gps_samples')

    op.drop_index(op.f('ix_captures_created_at'), table_name='captures')
    op.drop_index(op.f('ix_captures_session_id'), table_name='captures')
    op.drop_index(op.f('ix_captures_bin_id'), table_name='captures')
    op.drop_table('captures')

    op.drop_index(op.f('ix_bins_updated_at'), table_name='bins')
    op.drop_index(op.f('ix_bins_created_at'), table_name='bins')
    op.drop_index(op.f('ix_bins_bin_key'), table_name='bins')
    op.drop_table('bins')
