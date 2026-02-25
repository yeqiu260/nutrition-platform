"""add_admin_tables

Revision ID: 002_admin
Revises: 001_initial
Create Date: 2026-01-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_admin'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 先删除可能存在的枚举类型
    op.execute("DROP TYPE IF EXISTS userrole CASCADE")
    
    # 创建用户角色枚举
    userrole = postgresql.ENUM('user', 'partner', 'admin', 'super_admin', name='userrole', create_type=False)
    userrole.create(op.get_bind(), checkfirst=True)
    
    # 创建管理员用户表
    op.create_table('admin_users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', userrole, nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admin_users_username'), 'admin_users', ['username'], unique=True)
    
    # 创建系统配置表
    op.create_table('system_configs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('is_encrypted', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_configs_key'), 'system_configs', ['key'], unique=True)
    
    # 创建补充品表
    op.create_table('supplements',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('supplement_id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('group', sa.String(length=100), nullable=False),
        sa.Column('screening_threshold', sa.Integer(), nullable=True, server_default='2'),
        sa.Column('sort_order', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_supplements_supplement_id'), 'supplements', ['supplement_id'], unique=True)
    
    # 创建问卷问题表
    op.create_table('quiz_questions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('supplement_id', sa.String(length=50), nullable=False),
        sa.Column('phase', sa.String(length=20), nullable=False),
        sa.Column('subtitle', sa.String(length=100), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('options', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_questions_supplement_id'), 'quiz_questions', ['supplement_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_quiz_questions_supplement_id'), table_name='quiz_questions')
    op.drop_table('quiz_questions')
    op.drop_index(op.f('ix_supplements_supplement_id'), table_name='supplements')
    op.drop_table('supplements')
    op.drop_index(op.f('ix_system_configs_key'), table_name='system_configs')
    op.drop_table('system_configs')
    op.drop_index(op.f('ix_admin_users_username'), table_name='admin_users')
    op.drop_table('admin_users')
    
    # 删除枚举类型
    op.execute('DROP TYPE IF EXISTS userrole')
