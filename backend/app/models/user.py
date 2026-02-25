"""用户模型"""

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.core.database import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=True, index=True)
    
    # 认证相关
    password_hash = Column(String(255), nullable=True)  # 密码哈希（可选，OTP用户可能没有）
    account_type = Column(String(20), default="user", nullable=False)  # user / admin / partner
    is_verified = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # 个人信息
    full_name = Column(String(100), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)


class OTPCode(Base):
    """OTP 验证码表"""
    __tablename__ = "otp_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 接收方（邮箱或手机）
    recipient = Column(String(255), nullable=False, index=True)
    recipient_type = Column(String(10), nullable=False)  # 'email' or 'phone'
    
    # OTP 码
    code = Column(String(6), nullable=False)
    
    # 用途
    purpose = Column(String(20), nullable=False)  # 'login', 'register', 'verify'
    
    # 状态
    is_used = Column(Boolean, default=False, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)  # 尝试次数
    
    # 时间
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    
    # IP 追踪
    ip_address = Column(String(45), nullable=True)


class UserConsent(Base):
    """用户同意记录表"""
    __tablename__ = "user_consents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # 可为空（未注册用户）
    
    # 同意类型
    consent_type = Column(String(50), nullable=False)  # 'terms', 'privacy', 'health_data', 'marketing'
    
    # 同意状态
    is_agreed = Column(Boolean, nullable=False)
    
    # 版本号
    version = Column(String(20), nullable=False)  # 例如 'v1.0', 'v2.0'
    
    # 同意时的信息
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 撤销
    revoked_at = Column(DateTime, nullable=True)


class QuizSession(Base):
    """问卷会话表 - 记录每次问卷提交"""
    __tablename__ = "quiz_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # 可为空（匿名用户）
    
    # 会话信息
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # 问卷数据（JSON）
    answers = Column(JSONB, nullable=False)
    
    # 评分
    score = Column(Float, nullable=True)
    
    # AI 推荐结果（JSON）
    recommendations = Column(JSONB, nullable=True)
    
    # 状态
    status = Column(String(20), default='completed', nullable=False)  # 'completed', 'failed'
    ai_generated = Column(Boolean, default=False, nullable=False)
    
    # 时间
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # IP 追踪
    ip_address = Column(String(45), nullable=True)


class HealthProfile(Base):
    """健康档案表"""
    __tablename__ = "health_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    
    # 健康数据 (JSONB 存储列表)
    allergies = Column(JSONB, default=list)
    chronic_conditions = Column(JSONB, default=list)
    medications = Column(JSONB, default=list)
    goals = Column(JSONB, default=list)
    dietary_preferences = Column(JSONB, default=list)
    
    # 预算范围
    budget_min = Column(Float, nullable=True)
    budget_max = Column(Float, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
