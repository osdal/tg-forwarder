"""add pipeline and gemini key

Revision ID: 759573ddcfee
Revises: 57dee2fcdb3b
Create Date: 2026-10-24 05:02:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '759573ddcfee'
down_revision: Union[str, None] = '57dee2fcdb3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Добавляем колонку pipeline_json в sources
    op.add_column('sources', sa.Column('pipeline_json', sa.Text(), nullable=True))
    
    # Добавляем колонку pipeline_applied в posts
    op.add_column('posts', sa.Column('pipeline_applied', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    
    # Добавляем колонку gemini_api_key в app_settings
    op.add_column('app_settings', sa.Column('gemini_api_key', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('app_settings', 'gemini_api_key')
    op.drop_column('posts', 'pipeline_applied')
    op.drop_column('sources', 'pipeline_json')