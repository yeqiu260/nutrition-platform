"""OTP 验证码服务"""

import random
import string
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.user import OTPCode, User
from app.services.email_service import email_service


class OTPService:
    """OTP 验证码服务"""
    
    def __init__(
        self,
        code_length: int = 6,
        expiry_minutes: int = 10,
        max_attempts: int = 3
    ):
        self.code_length = code_length
        self.expiry_minutes = expiry_minutes
        self.max_attempts = max_attempts
    
    def _generate_code(self) -> str:
        """生成随机验证码"""
        return ''.join(random.choices(string.digits, k=self.code_length))
    
    async def create_otp(
        self,
        db: AsyncSession,
        recipient: str,
        recipient_type: str,  # 'email' or 'phone'
        purpose: str,  # 'login', 'register', 'verify'
        ip_address: Optional[str] = None
    ) -> str:
        """
        创建 OTP 验证码并发送
        
        Returns:
            验证码（用于发送给用户）
        """
        # 生成验证码
        code = self._generate_code()
        
        # 计算过期时间
        expires_at = datetime.utcnow() + timedelta(minutes=self.expiry_minutes)
        
        # 创建记录
        otp = OTPCode(
            id=str(uuid4()),
            recipient=recipient,
            recipient_type=recipient_type,
            code=code,
            purpose=purpose,
            is_used=False,
            attempts=0,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            ip_address=ip_address
        )
        
        db.add(otp)
        await db.commit()
        
        # 发送邮件（如果是邮箱）
        if recipient_type == 'email':
            try:
                await email_service.send_otp_email(
                    to_email=recipient,
                    otp_code=code,
                    purpose=purpose
                )
            except Exception as e:
                # 邮件发送失败不影响 OTP 创建
                import logging
                logging.error(f"Failed to send OTP email: {e}")
        
        # TODO: 发送短信（如果是手机号）
        # if recipient_type == 'phone':
        #     await sms_service.send_otp_sms(recipient, code)
        
        return code
    
    async def verify_otp(
        self,
        db: AsyncSession,
        recipient: str,
        code: str,
        purpose: str
    ) -> bool:
        """
        验证 OTP 验证码
        
        Returns:
            True if valid, raises HTTPException if invalid
        """
        # 查找最新的未使用的验证码
        result = await db.execute(
            select(OTPCode)
            .where(
                OTPCode.recipient == recipient,
                OTPCode.purpose == purpose,
                OTPCode.is_used == False
            )
            .order_by(OTPCode.created_at.desc())
            .limit(1)
        )
        otp = result.scalar_one_or_none()
        
        if not otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码不存在或已使用"
            )
        
        # 检查是否过期
        if datetime.utcnow() > otp.expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码已过期"
            )
        
        # 检查尝试次数
        if otp.attempts >= self.max_attempts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码尝试次数过多，请重新获取"
            )
        
        # 验证码错误
        if otp.code != code:
            otp.attempts += 1
            await db.commit()
            
            remaining = self.max_attempts - otp.attempts
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"验证码错误，还剩 {remaining} 次尝试机会"
            )
        
        # 验证成功，标记为已使用
        otp.is_used = True
        otp.used_at = datetime.utcnow()
        await db.commit()
        
        return True
    
    async def get_or_create_user(
        self,
        db: AsyncSession,
        email: Optional[str] = None,
        phone: Optional[str] = None
    ) -> User:
        """
        获取或创建用户
        
        Args:
            email: 邮箱
            phone: 手机号
        
        Returns:
            User 对象
        """
        # 查找现有用户
        query = select(User)
        if email:
            query = query.where(User.email == email)
        elif phone:
            query = query.where(User.phone == phone)
        else:
            raise ValueError("必须提供 email 或 phone")
        
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            # 更新最后登录时间
            user.last_login_at = datetime.utcnow()
            await db.commit()
            return user
        
        # 创建新用户
        user = User(
            id=uuid4(),
            email=email or f"{phone}@phone.local",  # 如果只有手机号，生成临时邮箱
            phone=phone,
            is_verified=True,  # OTP 验证通过即视为已验证
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_login_at=datetime.utcnow()
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # 发送欢迎邮件
        if email:
            try:
                await email_service.send_welcome_email(
                    to_email=email,
                    user_name=user.full_name
                )
            except Exception as e:
                # 欢迎邮件发送失败不影响注册
                import logging
                logging.error(f"Failed to send welcome email: {e}")
        
        return user
    
    async def cleanup_expired(self, db: AsyncSession) -> int:
        """
        清理过期的 OTP 记录
        
        Returns:
            删除的记录数
        """
        result = await db.execute(
            select(OTPCode).where(
                OTPCode.expires_at < datetime.utcnow()
            )
        )
        expired_otps = result.scalars().all()
        
        for otp in expired_otps:
            await db.delete(otp)
        
        await db.commit()
        return len(expired_otps)


# 全局实例
otp_service = OTPService(
    code_length=6,
    expiry_minutes=10,
    max_attempts=3
)
