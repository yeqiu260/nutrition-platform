"""用户认证 API - OTP 登录/注册 + 密码登录"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings
from app.services.otp_service import otp_service
from app.services.consent_service import consent_service
from app.middleware.endpoint_limit import rate_limit
from app.models.user import User

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/auth", tags=["auth"])

# JWT 配置
JWT_SECRET = settings.jwt_secret_key
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


# ============================================================================
# 工具函数
# ============================================================================

def hash_password(password: str) -> str:
    """哈希密码"""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${pwd_hash.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    try:
        salt, pwd_hash = hashed.split('$')
        new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return new_hash.hex() == pwd_hash
    except:
        return False


def create_jwt_token(user_id: str, email: str, account_type: str = "user") -> str:
    """创建 JWT Token"""
    payload = {
        "sub": user_id,
        "email": email,
        "account_type": account_type,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ============================================================================
# 请求/响应模型
# ============================================================================

class SendOTPRequest(BaseModel):
    """发送 OTP 请求"""
    email: Optional[EmailStr] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, description="手机号")
    purpose: str = Field(..., description="用途: login, register, verify")


class VerifyOTPRequest(BaseModel):
    """验证 OTP 请求"""
    email: Optional[EmailStr] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, description="手机号")
    code: str = Field(..., description="验证码", min_length=6, max_length=6)
    purpose: str = Field(..., description="用途: login, register, verify")
    
    # 同意条款（注册时必填）
    consents: Optional[dict] = Field(None, description="同意条款 {consent_type: is_agreed}")


class RegisterRequest(BaseModel):
    """注册请求 - 邮箱 + OTP + 密码"""
    email: EmailStr = Field(..., description="邮箱")
    otp_code: str = Field(..., description="OTP 验证码", min_length=6, max_length=6)
    password: str = Field(..., description="密码", min_length=6, max_length=100)
    full_name: Optional[str] = Field(None, description="姓名")
    consents: Optional[dict] = Field(None, description="同意条款")


class LoginRequest(BaseModel):
    """密码登录请求"""
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., description="密码")


class SetPasswordRequest(BaseModel):
    """设置密码请求"""
    email: EmailStr = Field(..., description="邮箱")
    otp_code: str = Field(..., description="OTP 验证码", min_length=6, max_length=6)
    new_password: str = Field(..., description="新密码", min_length=6, max_length=100)


class AuthResponse(BaseModel):
    """认证响应"""
    success: bool
    message: str
    user_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    token: Optional[str] = None
    account_type: Optional[str] = None
    is_new_user: bool = False


class ConsentInfo(BaseModel):
    """同意条款信息"""
    consent_type: str
    description: str
    required: bool


class ConsentsResponse(BaseModel):
    """同意条款列表响应"""
    required: list[ConsentInfo]
    optional: list[ConsentInfo]
    current_version: str


# ============================================================================
# API 端点
# ============================================================================

@router.get("/consents", response_model=ConsentsResponse)
async def get_consents():
    """
    获取需要用户同意的条款列表
    
    返回必需和可选的同意项
    """
    required = await consent_service.get_required_consents()
    optional = await consent_service.get_optional_consents()
    
    return ConsentsResponse(
        required=[
            ConsentInfo(consent_type=k, description=v, required=True)
            for k, v in required.items()
        ],
        optional=[
            ConsentInfo(consent_type=k, description=v, required=False)
            for k, v in optional.items()
        ],
        current_version=consent_service.CURRENT_VERSION
    )


@router.post("/send-otp", response_model=AuthResponse)
@rate_limit(max_requests=5, window=60)  # 每分钟最多 5 次
async def send_otp(
    request: Request,
    otp_request: SendOTPRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    发送 OTP 验证码
    
    限制：每分钟最多 5 次请求
    
    Args:
        email: 邮箱（email 和 phone 至少提供一个）
        phone: 手机号
        purpose: 用途（login, register, verify）
    
    Returns:
        成功消息（实际验证码会通过邮件/短信发送）
    """
    # 验证输入
    if not otp_request.email and not otp_request.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须提供邮箱或手机号"
        )
    
    if otp_request.purpose not in ['login', 'register', 'verify']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的用途"
        )
    
    # 获取 IP 地址
    client_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    
    # 确定接收方和类型
    recipient = otp_request.email or otp_request.phone
    recipient_type = "email" if otp_request.email else "phone"
    
    # 生成 OTP
    code = await otp_service.create_otp(
        db=db,
        recipient=recipient,
        recipient_type=recipient_type,
        purpose=otp_request.purpose,
        ip_address=client_ip
    )
    
    # 开发环境：打印验证码到控制台
    # 生产环境：应该注释掉这部分
    logger.info(f"OTP Code for {recipient}: {code}")
    if settings.debug:
        print(f"=" * 80)
        print(f"OTP 验证码已生成（开发模式）")
        print(f"接收方: {recipient}")
        print(f"验证码: {code}")
        print(f"用途: {otp_request.purpose}")
        print(f"有效期: 10 分钟")
        print(f"=" * 80)
    
    return AuthResponse(
        success=True,
        message=f"验证码已发送到 {recipient}，有效期 10 分钟"
    )


@router.post("/verify-otp", response_model=AuthResponse)
@rate_limit(max_requests=10, window=60)  # 每分钟最多 10 次
async def verify_otp(
    request: Request,
    verify_request: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    验证 OTP 并登录/注册
    
    限制：每分钟最多 10 次请求
    
    Args:
        email: 邮箱
        phone: 手机号
        code: 验证码
        purpose: 用途
        consents: 同意条款（注册时必填）
    
    Returns:
        用户信息和认证状态
    """
    # 验证输入
    if not verify_request.email and not verify_request.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须提供邮箱或手机号"
        )
    
    # 确定接收方
    recipient = verify_request.email or verify_request.phone
    
    # 验证 OTP
    await otp_service.verify_otp(
        db=db,
        recipient=recipient,
        code=verify_request.code,
        purpose=verify_request.purpose
    )
    
    # 获取或创建用户
    user = await otp_service.get_or_create_user(
        db=db,
        email=verify_request.email,
        phone=verify_request.phone
    )
    
    is_new_user = user.created_at == user.last_login_at
    
    # 记录同意条款
    if verify_request.consents:
        # 获取 IP 和 User Agent
        client_ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        
        user_agent = request.headers.get("User-Agent")
        
        # 检查必需的同意项
        required_consents = await consent_service.get_required_consents()
        for consent_type in required_consents.keys():
            if consent_type not in verify_request.consents:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"必须同意 {required_consents[consent_type]}"
                )
            if not verify_request.consents[consent_type]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"必须同意 {required_consents[consent_type]}"
                )
        
        # 记录所有同意
        await consent_service.record_all_consents(
            db=db,
            user_id=user.id,
            consents=verify_request.consents,
            ip_address=client_ip,
            user_agent=user_agent
        )
    
    logger.info(f"User {'registered' if is_new_user else 'logged in'}: {user.email}")
    
    return AuthResponse(
        success=True,
        message="登录成功" if not is_new_user else "注册成功",
        user_id=str(user.id),
        email=user.email,
        phone=user.phone,
        is_new_user=is_new_user
    )


@router.get("/check-consent/{user_id}/{consent_type}")
async def check_user_consent(
    user_id: str,
    consent_type: str,
    db: AsyncSession = Depends(get_db)
):
    """
    检查用户是否同意某项条款
    
    Args:
        user_id: 用户 ID
        consent_type: 同意类型
    
    Returns:
        是否同意
    """
    from uuid import UUID
    
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的用户 ID"
        )
    
    is_agreed = await consent_service.check_consent(
        db=db,
        user_id=user_uuid,
        consent_type=consent_type
    )
    
    return {
        "user_id": user_id,
        "consent_type": consent_type,
        "is_agreed": is_agreed
    }


# ============================================================================
# 密码认证 API 端点
# ============================================================================

@router.post("/register", response_model=AuthResponse)
@rate_limit(max_requests=5, window=60)
async def register_with_password(
    request: Request,
    register_request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    使用邮箱 + OTP + 密码注册
    
    流程：
    1. 先调用 /send-otp 获取验证码
    2. 调用此接口完成注册
    """
    # 验证 OTP
    await otp_service.verify_otp(
        db=db,
        recipient=register_request.email,
        code=register_request.otp_code,
        purpose="register"
    )
    
    # 检查邮箱是否已注册
    result = await db.execute(
        select(User).where(User.email == register_request.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user and existing_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="該郵箱已註冊，請直接登入"
        )
    
    # 创建或更新用户
    if existing_user:
        # 已有 OTP 用户，添加密码
        existing_user.password_hash = hash_password(register_request.password)
        existing_user.is_verified = True
        if register_request.full_name:
            existing_user.full_name = register_request.full_name
        user = existing_user
    else:
        # 新用户
        user = User(
            email=register_request.email,
            password_hash=hash_password(register_request.password),
            full_name=register_request.full_name,
            is_verified=True,
            account_type="user"
        )
        db.add(user)
    
    await db.commit()
    await db.refresh(user)
    
    # 生成 JWT
    token = create_jwt_token(str(user.id), user.email, user.account_type)
    
    logger.info(f"User registered: {user.email}")
    
    return AuthResponse(
        success=True,
        message="註冊成功",
        user_id=str(user.id),
        email=user.email,
        token=token,
        account_type=user.account_type,
        is_new_user=True
    )


@router.post("/login", response_model=AuthResponse)
@rate_limit(max_requests=10, window=60)
async def login_with_password(
    request: Request,
    login_request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    使用邮箱 + 密码登录
    
    返回 JWT Token 用于后续认证
    """
    # 查找用户
    result = await db.execute(
        select(User).where(User.email == login_request.email)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="郵箱或密碼錯誤"
        )
    
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="該帳戶未設置密碼，請使用 OTP 登入或重設密碼"
        )
    
    if not verify_password(login_request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="郵箱或密碼錯誤"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="帳戶已被停用"
        )
    
    # 更新最后登录时间
    user.last_login_at = datetime.utcnow()
    await db.commit()
    
    # 生成 JWT
    token = create_jwt_token(str(user.id), user.email, user.account_type)
    
    logger.info(f"User logged in: {user.email}")
    
    return AuthResponse(
        success=True,
        message="登入成功",
        user_id=str(user.id),
        email=user.email,
        phone=user.phone,
        token=token,
        account_type=user.account_type,
        is_new_user=False
    )


@router.post("/set-password", response_model=AuthResponse)
@rate_limit(max_requests=5, window=60)
async def set_password(
    request: Request,
    set_pwd_request: SetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    设置/重置密码
    
    需要先通过 OTP 验证
    """
    # 验证 OTP
    await otp_service.verify_otp(
        db=db,
        recipient=set_pwd_request.email,
        code=set_pwd_request.otp_code,
        purpose="verify"
    )
    
    # 查找用户
    result = await db.execute(
        select(User).where(User.email == set_pwd_request.email)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用戶不存在"
        )
    
    # 更新密码
    user.password_hash = hash_password(set_pwd_request.new_password)
    await db.commit()
    
    # 生成 JWT
    token = create_jwt_token(str(user.id), user.email, user.account_type)
    
    logger.info(f"Password set for user: {user.email}")
    
    return AuthResponse(
        success=True,
        message="密碼設置成功",
        user_id=str(user.id),
        email=user.email,
        token=token,
        account_type=user.account_type
    )

