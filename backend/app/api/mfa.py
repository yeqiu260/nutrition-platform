"""MFA 多因素验证 API

实现 TOTP 双因素认证
"""

import base64
import hashlib
import hmac
import secrets
import struct
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.admin import AdminUser, UserRole
from app.api.admin import get_current_admin, require_role

router = APIRouter(prefix="/api/admin/mfa", tags=["mfa"])


class MFASetupResponse(BaseModel):
    """MFA 设置响应"""
    secret: str
    qr_uri: str
    backup_codes: list[str]


class MFAVerifyRequest(BaseModel):
    """MFA 验证请求"""
    code: str


class MFAVerifyResponse(BaseModel):
    """MFA 验证响应"""
    valid: bool
    message: str


def generate_totp_secret() -> str:
    """生成 TOTP 密钥"""
    return base64.b32encode(secrets.token_bytes(20)).decode('utf-8')


def get_totp_uri(secret: str, username: str, issuer: str = "WysikHealth") -> str:
    """生成 TOTP URI（用于二维码）"""
    return f"otpauth://totp/{issuer}:{username}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"


def generate_totp(secret: str, time_step: int = 30) -> str:
    """生成 TOTP 代码"""
    key = base64.b32decode(secret.upper())
    counter = int(time.time()) // time_step
    counter_bytes = struct.pack('>Q', counter)
    
    hmac_hash = hmac.new(key, counter_bytes, hashlib.sha1).digest()
    offset = hmac_hash[-1] & 0x0F
    code = struct.unpack('>I', hmac_hash[offset:offset + 4])[0]
    code = (code & 0x7FFFFFFF) % 1000000
    
    return str(code).zfill(6)


def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    """验证 TOTP 代码
    
    Args:
        secret: TOTP 密钥
        code: 用户输入的代码
        window: 时间窗口（前后允许的时间步数）
    """
    for i in range(-window, window + 1):
        time_step = 30
        counter = int(time.time()) // time_step + i
        
        key = base64.b32decode(secret.upper())
        counter_bytes = struct.pack('>Q', counter)
        
        hmac_hash = hmac.new(key, counter_bytes, hashlib.sha1).digest()
        offset = hmac_hash[-1] & 0x0F
        expected_code = struct.unpack('>I', hmac_hash[offset:offset + 4])[0]
        expected_code = (expected_code & 0x7FFFFFFF) % 1000000
        
        if code == str(expected_code).zfill(6):
            return True
    
    return False


def generate_backup_codes(count: int = 10) -> list[str]:
    """生成备用恢复代码"""
    return [secrets.token_hex(4).upper() for _ in range(count)]


@router.post("/setup", response_model=MFASetupResponse)
async def setup_mfa(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """
    设置 MFA
    
    生成 TOTP 密钥和二维码 URI
    """
    if admin.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA 已启用，请先禁用后再重新设置"
        )
    
    # 生成密钥
    secret = generate_totp_secret()
    qr_uri = get_totp_uri(secret, admin.username)
    backup_codes = generate_backup_codes()
    
    # 临时存储密钥（验证成功后才正式启用）
    admin.mfa_secret = secret
    await db.commit()
    
    return MFASetupResponse(
        secret=secret,
        qr_uri=qr_uri,
        backup_codes=backup_codes
    )


@router.post("/verify", response_model=MFAVerifyResponse)
async def verify_mfa(
    request: MFAVerifyRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """
    验证 MFA 代码并启用
    
    首次设置时验证成功后启用 MFA
    """
    if not admin.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="請先設置 MFA"
        )
    
    if verify_totp(admin.mfa_secret, request.code):
        if not admin.mfa_enabled:
            admin.mfa_enabled = True
            await db.commit()
        
        return MFAVerifyResponse(
            valid=True,
            message="MFA 驗證成功，已啟用雙因素認證"
        )
    else:
        return MFAVerifyResponse(
            valid=False,
            message="驗證碼錯誤，請重試"
        )


@router.post("/disable")
async def disable_mfa(
    request: MFAVerifyRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """
    禁用 MFA
    
    需要验证当前 TOTP 代码
    """
    if not admin.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA 未啟用"
        )
    
    if not verify_totp(admin.mfa_secret, request.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="驗證碼錯誤"
        )
    
    admin.mfa_enabled = False
    admin.mfa_secret = None
    await db.commit()
    
    return {"message": "MFA 已禁用"}


@router.get("/status")
async def get_mfa_status(
    admin: AdminUser = Depends(get_current_admin),
):
    """获取 MFA 状态"""
    return {
        "enabled": admin.mfa_enabled,
        "has_secret": admin.mfa_secret is not None
    }
