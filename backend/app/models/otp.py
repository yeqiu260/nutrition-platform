"""OTP (One-Time Password) 相关模型"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OTPCode(Base):
    """OTP 验证码模型"""

    __tablename__ = "otp_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contact: Mapped[str] = mapped_column(String(255), index=True)  # 手机号或邮箱
    contact_type: Mapped[str] = mapped_column(String(20))  # "phone" | "email"
    code: Mapped[str] = mapped_column(String(10))  # 验证码（6位数字）
    purpose: Mapped[str] = mapped_column(String(20))  # "login" | "register" | "verify"
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    is_expired: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)  # 验证尝试次数
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)  # 最大尝试次数
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.utcnow() + timedelta(minutes=10)
    )  # 10分钟过期
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    def is_valid(self) -> bool:
        """检查 OTP 是否有效"""
        if self.is_used:
            return False
        if self.is_expired:
            return False
        if datetime.utcnow() > self.expires_at:
            self.is_expired = True
            return False
        if self.attempts >= self.max_attempts:
            return False
        return True

    def mark_as_used(self):
        """标记为已使用"""
        self.is_used = True
        self.used_at = datetime.utcnow()

    def increment_attempts(self):
        """增加尝试次数"""
        self.attempts += 1
