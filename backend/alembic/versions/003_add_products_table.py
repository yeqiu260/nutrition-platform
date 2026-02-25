"""add_products_table

Revision ID: 003_products
Revises: 002_admin
Create Date: 2026-01-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '003_products'
down_revision: Union[str, None] = '002_admin'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('products',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=True, server_default='TWD'),
        sa.Column('supplement_id', sa.String(length=50), nullable=False),
        sa.Column('purchase_url', sa.String(length=500), nullable=False),
        sa.Column('partner_id', sa.UUID(), nullable=False),
        sa.Column('partner_name', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('is_approved', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('sort_order', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['partner_id'], ['admin_users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_products_supplement_id'), 'products', ['supplement_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_products_supplement_id'), table_name='products')
    op.drop_table('products')
