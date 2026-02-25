"""管理员相关数据模型"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class UserRole(str, Enum):
    """用户角色"""
    USER = "user"           # 普通用户
    PARTNER = "partner"     # 合作商
    ADMIN = "admin"         # 管理员
    SUPER_ADMIN = "super_admin"  # 超级管理员


class AdminUser(Base):
    """管理员用户表"""
    __tablename__ = "admin_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole, values_callable=lambda x: [e.value for e in x]), default=UserRole.ADMIN, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), nullable=True)  # 创建者ID
    
    # 【MFA 多因素验证】
    mfa_enabled = Column(Boolean, default=False)  # 是否启用 MFA
    mfa_secret = Column(String(255), nullable=True)  # TOTP 密钥（加密存储）


class SystemConfig(Base):
    """系统配置表 - 存储 API Key 等配置"""
    __tablename__ = "system_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    description = Column(String(255), nullable=True)
    is_encrypted = Column(Boolean, default=False)  # 是否加密存储
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(UUID(as_uuid=True), nullable=True)


class QuizQuestion(Base):
    """问卷问题表 - 可动态管理的问题"""
    __tablename__ = "quiz_questions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    supplement_id = Column(String(50), nullable=False, index=True)  # 关联的补充品ID
    phase = Column(String(20), nullable=False)  # screening 或 detail
    subtitle = Column(String(100), nullable=False)
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)  # [{label: "", score: 0}, ...]
    sort_order = Column(Integer, default=0)  # 排序
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Supplement(Base):
    """补充品表 - 可动态管理的补充品"""
    __tablename__ = "supplements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    supplement_id = Column(String(50), unique=True, nullable=False, index=True)  # 如 vitamin_d
    name = Column(String(100), nullable=False)
    group = Column(String(100), nullable=False)
    screening_threshold = Column(Integer, default=2)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
