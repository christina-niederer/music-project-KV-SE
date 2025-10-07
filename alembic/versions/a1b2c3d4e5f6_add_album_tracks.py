"""add album tracks association

Revision ID: a1b2c3d4e5f6
Revises: 9805747b3561
Create Date: 2025-10-07 20:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9805747b3561'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'album_tracks',
        sa.Column('album_id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('track_number', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['album_id'], ['music_items.id'], name='fk_album_tracks_album'),
        sa.ForeignKeyConstraint(['track_id'], ['music_items.id'], name='fk_album_tracks_track'),
        sa.PrimaryKeyConstraint('album_id', 'track_id', name='pk_album_tracks')
    )
    op.create_index('ix_album_tracks_album', 'album_tracks', ['album_id'])
    op.create_index('ix_album_tracks_track', 'album_tracks', ['track_id'])


def downgrade() -> None:
    op.drop_index('ix_album_tracks_album', table_name='album_tracks')
    op.drop_index('ix_album_tracks_track', table_name='album_tracks')
    op.drop_table('album_tracks')
