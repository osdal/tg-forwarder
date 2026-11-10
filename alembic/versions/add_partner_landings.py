"""add partner landings and clicks

Revision ID: a1b2c3d4e5f6
Revises: 9e2a1b3c4d5f
Create Date: 2026-11-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '9e2a1b3c4d5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'partner_landings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('postback_url', sa.String(), nullable=True),
        sa.Column('secret', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_partner_landings_name'), 'partner_landings', ['name'], unique=False)

    op.create_table(
        'partner_clicks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('landing_id', sa.Integer(), nullable=False),
        sa.Column('ip_hash', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('referrer', sa.String(), nullable=True),
        sa.Column('utm_source', sa.String(), nullable=True),
        sa.Column('utm_medium', sa.String(), nullable=True),
        sa.Column('utm_campaign', sa.String(), nullable=True),
        sa.Column('utm_content', sa.String(), nullable=True),
        sa.Column('utm_term', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['landing_id'], ['partner_landings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_partner_clicks_landing_id'), 'partner_clicks', ['landing_id'], unique=False)
    op.create_index(op.f('ix_partner_clicks_created_at'), 'partner_clicks', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_partner_clicks_created_at'), table_name='partner_clicks')
    op.drop_index(op.f('ix_partner_clicks_landing_id'), table_name='partner_clicks')
    op.drop_table('partner_clicks')
    op.drop_index(op.f('ix_partner_landings_name'), table_name='partner_landings')
    op.drop_table('partner_landings')