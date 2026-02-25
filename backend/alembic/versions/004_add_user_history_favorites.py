"""add user history and favorites tables

Revision ID: 004
Revises: 578ef917c229
Create Date: 2026-01-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '578ef917c229'  # 修正为正确的上一个版本
branch_labels = None
depends_on = None


def upgrade():
    # 创建问卷历史记录表
    op.create_table(
        'quiz_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(100), nullable=False, unique=True),
        sa.Column('answers', postgresql.JSON, nullable=False),
        sa.Column('health_data', postgresql.JSON, nullable=True),
        sa.Column('recommendations', postgresql.JSON, nullable=False),
        sa.Column('ai_generated', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # 创建索引
    op.create_index('ix_quiz_history_user_id', 'quiz_history', ['user_id'])
    op.create_index('ix_quiz_history_session_id', 'quiz_history', ['session_id'])
    op.create_index('ix_quiz_history_created_at', 'quiz_history', ['created_at'])
    
    # 创建收藏商品表
    op.create_table(
        'favorite_products',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('note', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
    )
    
    # 创建索引和唯一约束
    op.create_index('ix_favorite_products_user_id', 'favorite_products', ['user_id'])
    op.create_index('ix_favorite_products_product_id', 'favorite_products', ['product_id'])
    op.create_index('ix_favorite_products_created_at', 'favorite_products', ['created_at'])
    op.create_unique_constraint('uq_user_product', 'favorite_products', ['user_id', 'product_id'])


def downgrade():
    op.drop_table('favorite_products')
    op.drop_table('quiz_history')
