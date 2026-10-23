"""merge multiple heads

Revision ID: 57dee2fcdb3b
Revises: 000dbd575e45, 6e97864bd677
Create Date: 2026-10-23 06:48:08.148753

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '57dee2fcdb3b'
down_revision: Union[str, None] = ('000dbd575e45', '6e97864bd677')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass