"""add_ai_usage_tracking

Revision ID: fc0f9c9a7643
Revises: 003_products
Create Date: 2026-01-17 21:48:51.859068

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc0f9c9a7643'
down_revision: Union[str, None] = '003_products'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 AI 使用量跟踪表
    op.create_table(
        'ai_usage',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_identifier', sa.String(), nullable=False),
        sa.Column('usage_date', sa.Date(), nullable=False),
        sa.Column('call_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_call_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建索引
    op.create_index('idx_user_date', 'ai_usage', ['user_identifier', 'usage_date'])
    op.create_index(op.f('ix_ai_usage_user_identifier'), 'ai_usage', ['user_identifier'])
    op.create_index(op.f('ix_ai_usage_usage_date'), 'ai_usage', ['usage_date'])


def downgrade() -> None:
    # 删除索引
    op.drop_index(op.f('ix_ai_usage_usage_date'), table_name='ai_usage')
    op.drop_index(op.f('ix_ai_usage_user_identifier'), table_name='ai_usage')
    op.drop_index('idx_user_date', table_name='ai_usage')
    
    # 删除表
    op.drop_table('ai_usage')
