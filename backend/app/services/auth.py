"""认证服务 - OTP 发送、验证、JWT token 生成和同意记录"""

import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import jwt
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import AsyncSession
from app.models.user import Consent, User

settings = get_settings()


class OTPResponse(BaseModel):
    """OTP 发送响应"""

    request_id: str
    expires_at: datetime


class AuthResult(BaseModel):
    """认证结果"""

    token: str
    user_id: str
    expires_at: datetime


class ConsentRecord(BaseModel):
    """同意记录"""

    health_data_consent: bool
    marketing_consent: bool
    version: str


class ConsentStatus(BaseModel):
    """同意状态"""

    health_data_consented: bool
    marketing_consented: bool
    consent_version: Optional[str] = None


class AuthService:
    """认证服务"""

    def __init__(self, db: AsyncSession, redis: Redis):
        """初始化认证服务"""
        self.db = db
        self.redis = redis
        self.otp_expire_minutes = settings.otp_expire_minutes
        self.otp_max_attempts = settings.otp_max_attempts
        self.jwt_secret_key = settings.jwt_secret_key
        self.jwt_algorithm = settings.jwt_algorithm
        self.jwt_expire_minutes = settings.jwt_expire_minutes

    def _generate_otp(self, length: int = 6) -> str:
        """生成 OTP 码"""
        return "".join(random.choices(string.digits, k=length))

    def _generate_request_id(self) -> str:
        """生成请求 ID"""
        return "".join(random.choices(string.ascii_letters + string.digits, k=32))

    async def check_rate_limit(self, contact: str) -> bool:
        """
        检查联络方式是否超过速率限制

        Args:
            contact: 联络方式

        Returns:
            bool: 如果未超限返回 True，否则返回 False

        Raises:
            ValueError: 如果超过速率限制
        """
        rate_limit_key = f"otp_rate_limit:{contact}"
        attempts_str = await self.redis.get(rate_limit_key)
        attempts = int(attempts_str) if attempts_str else 0

        if attempts >= self.otp_max_attempts:
            raise ValueError(
                f"Rate limit exceeded for contact {contact}. "
                f"Maximum {self.otp_max_attempts} attempts allowed in {self.otp_expire_minutes} minutes."
            )

        return True

    async def send_otp(self, contact: str, contact_type: str) -> OTPResponse:
        """
        发送 OTP 到指定联络方式

        Args:
            contact: 联络方式（电话或邮箱）
            contact_type: 联络类型（"phone" 或 "email"）

        Returns:
            OTPResponse: 包含 request_id 和过期时间

        Raises:
            ValueError: 如果联络类型无效或超过速率限制
        """
        if contact_type not in ("phone", "email"):
            raise ValueError(f"Invalid contact_type: {contact_type}")

        # 检查速率限制
        await self.check_rate_limit(contact)

        # 生成 OTP 和 request_id
        otp_code = self._generate_otp()
        request_id = self._generate_request_id()

        # 计算过期时间
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.otp_expire_minutes)

        # 存储到 Redis
        otp_key = f"otp:{request_id}"
        otp_data = f"{otp_code}:{contact}:{contact_type}"
        await self.redis.setex(
            otp_key,
            self.otp_expire_minutes * 60,
            otp_data,
        )

        # 初始化尝试计数
        attempt_key = f"otp_attempts:{request_id}"
        await self.redis.setex(attempt_key, self.otp_expire_minutes * 60, "0")

        # 增加联络方式的速率限制计数
        rate_limit_key = f"otp_rate_limit:{contact}"
        await self.redis.incr(rate_limit_key)
        await self.redis.expire(rate_limit_key, self.otp_expire_minutes * 60)

        # TODO: 实际发送 OTP（SMS/Email）
        # 这里仅作演示，实际应调用 SMS/Email 服务
        # 开发模式下使用固定 OTP: 123456
        if settings.debug:
            otp_code = "123456"
            # 重新存储固定的 OTP
            otp_data = f"{otp_code}:{contact}:{contact_type}"
            await self.redis.setex(
                otp_key,
                self.otp_expire_minutes * 60,
                otp_data,
            )
        print(f"[DEBUG] OTP sent to {contact} ({contact_type}): {otp_code}")

        return OTPResponse(request_id=request_id, expires_at=expires_at)

    async def verify_otp(
        self, request_id: str, code: str, ip_address: str
    ) -> AuthResult:
        """
        验证 OTP 并返回 JWT token

        Args:
            request_id: OTP 请求 ID
            code: 用户输入的 OTP 码
            ip_address: 用户 IP 地址

        Returns:
            AuthResult: 包含 JWT token 和用户信息

        Raises:
            ValueError: 如果 OTP 无效、过期或尝试次数超限
        """
        # 检查尝试次数
        attempt_key = f"otp_attempts:{request_id}"
        attempts_str = await self.redis.get(attempt_key)
        attempts = int(attempts_str) if attempts_str else 0

        if attempts >= self.otp_max_attempts:
            raise ValueError("OTP verification attempts exceeded")

        # 获取存储的 OTP
        otp_key = f"otp:{request_id}"
        otp_data = await self.redis.get(otp_key)

        if not otp_data:
            raise ValueError("OTP expired or not found")

        stored_otp, contact, contact_type = otp_data.split(":")

        # 验证 OTP 码
        if code != stored_otp:
            # 增加尝试计数
            await self.redis.incr(attempt_key)
            raise ValueError("Invalid OTP code")

        # OTP 验证成功，删除 OTP 数据
        await self.redis.delete(otp_key)
        await self.redis.delete(attempt_key)

        # 获取或创建用户
        user = await self._get_or_create_user(contact, contact_type)

        # 更新最后登入时间
        user.last_login_at = datetime.utcnow()
        self.db.add(user)
        await self.db.commit()

        # 生成 JWT token
        token = self._generate_jwt_token(user.id)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.jwt_expire_minutes)

        return AuthResult(
            token=token,
            user_id=str(user.id),
            expires_at=expires_at,
        )

    async def _get_or_create_user(self, contact: str, contact_type: str) -> User:
        """获取或创建用户"""
        from sqlalchemy import select

        # 查询现有用户
        stmt = select(User).where(User.contact == contact)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            return user

        # 创建新用户 - 使用 UTC 时间但不带时区信息（数据库列是 timestamp without time zone）
        user = User(
            contact=contact,
            contact_type=contact_type,
            role="user",
            mfa_enabled=False,
            created_at=datetime.utcnow(),
        )
        self.db.add(user)
        await self.db.flush()
        return user

    def _generate_jwt_token(self, user_id: UUID) -> str:
        """生成 JWT token"""
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=self.jwt_expire_minutes)

        payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": expires_at,
        }

        token = jwt.encode(payload, self.jwt_secret_key, algorithm=self.jwt_algorithm)
        return token

    def verify_jwt_token(self, token: str) -> Optional[str]:
        """
        验证 JWT token 并返回 user_id

        Args:
            token: JWT token

        Returns:
            user_id: 如果有效返回用户 ID，否则返回 None
        """
        try:
            payload = jwt.decode(token, self.jwt_secret_key, algorithms=[self.jwt_algorithm])
            return payload.get("sub")
        except jwt.InvalidTokenError:
            return None

    async def record_consent(
        self, user_id: UUID, consent: ConsentRecord, ip_address: str
    ) -> None:
        """
        记录用户同意

        Args:
            user_id: 用户 ID
            consent: 同意记录
            ip_address: 用户 IP 地址
        """
        consent_record = Consent(
            user_id=user_id,
            health_data_consent=consent.health_data_consent,
            marketing_consent=consent.marketing_consent,
            version=consent.version,
            ip_address=ip_address,
            consented_at=datetime.utcnow(),
        )
        self.db.add(consent_record)
        await self.db.commit()

    async def check_consent(self, user_id: UUID) -> ConsentStatus:
        """
        检查用户同意状态

        Args:
            user_id: 用户 ID

        Returns:
            ConsentStatus: 用户的同意状态
        """
        # 获取最新的同意记录
        stmt = (
            select(Consent)
            .where(Consent.user_id == user_id)
            .order_by(Consent.consented_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        consent = result.scalar_one_or_none()

        if not consent:
            return ConsentStatus(
                health_data_consented=False,
                marketing_consented=False,
                consent_version=None,
            )

        return ConsentStatus(
            health_data_consented=consent.health_data_consent,
            marketing_consented=consent.marketing_consent,
            consent_version=consent.version,
        )
