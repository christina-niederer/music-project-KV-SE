"""add track files table

Revision ID: b2c3d4e5f6
Revises: a1b2c3d4e5f6
Create Date: 2025-10-07 21:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'track_files',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.VARCHAR(length=500), nullable=False),
        sa.Column('content_type', sa.VARCHAR(length=120), nullable=True),
        sa.Column('file_data', sa.LargeBinary(), nullable=False),
        sa.Column('compressed', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('original_size', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['track_id'], ['music_items.id'], name='fk_track_files_track'),
        sa.UniqueConstraint('track_id', name='uq_track_file_track')
    )
    op.create_index('ix_track_files_track', 'track_files', ['track_id'])


def downgrade() -> None:
    op.drop_index('ix_track_files_track', table_name='track_files')
    op.drop_table('track_files')
