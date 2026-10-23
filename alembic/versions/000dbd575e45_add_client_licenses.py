"""add client licenses

Revision ID: 000dbd575e45
Revises: 123624345fb7
Create Date: 2026-10-23 06:41:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '000dbd575e45'
down_revision: Union[str, None] = '123624345fb7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'client_licenses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_name', sa.String(), nullable=True),
        sa.Column('license_key', sa.Text(), nullable=True),
        sa.Column('plan', sa.String(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_client_licenses_client_name'), 'client_licenses', ['client_name'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_client_licenses_client_name'), table_name='client_licenses')
    op.drop_table('client_licenses')