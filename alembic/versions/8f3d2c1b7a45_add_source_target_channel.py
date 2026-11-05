"""add target_channel_id to sources

Revision ID: 8f3d2c1b7a45
Revises: 759573ddcfee
Create Date: 2026-11-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8f3d2c1b7a45'
down_revision: Union[str, None] = '759573ddcfee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sources', sa.Column('target_channel_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_sources_target_channel_id',
        'sources', 'target_channels',
        ['target_channel_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_sources_target_channel_id', 'sources', type_='foreignkey')
    op.drop_column('sources', 'target_channel_id')
