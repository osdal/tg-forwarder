"""add umami fields to app_settings

Revision ID: 9e2a1b3c4d5f
Revises: 8f3d2c1b7a45
Create Date: 2026-11-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9e2a1b3c4d5f'
down_revision: Union[str, None] = '8f3d2c1b7a45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('app_settings', sa.Column('umami_website_id', sa.String(), nullable=True))
    op.add_column('app_settings', sa.Column('umami_url', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('app_settings', 'umami_url')
    op.drop_column('app_settings', 'umami_website_id')