"""安全与权限模块 - RBAC、IDOR 防护、PII 遮罩"""

import re
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import wraps
from typing import Callable, List, Optional, Set
from uuid import UUID

from fastapi import HTTPException, Request
from pydantic import BaseModel


class Role(str, Enum):
    """用户角色枚举"""
    ADMIN = "admin"           # 管理员 - 完全访问权限
    OPERATOR = "operator"     # 运营 - 配置管理、商品管理
    REVIEWER = "reviewer"     # 审核员 - 审核队列访问
    ANALYST = "analyst"       # 分析师 - 只读分析数据
    SUPPORT = "support"       # 客服 - 用户查询、有限修改
    USER = "user"             # 普通用户 - 基本功能


class Permission(str, Enum):
    """权限枚举"""
    # 用户管理
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    
    # 配置管理
    CONFIG_READ = "config:read"
    CONFIG_WRITE = "config:write"
    CONFIG_DEPLOY = "config:deploy"
    CONFIG_ROLLBACK = "config:rollback"
    
    # 审核队列
    REVIEW_READ = "review:read"
    REVIEW_WRITE = "review:write"
    
    # 分析数据
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"
    
    # 商品管理
    PRODUCT_READ = "product:read"
    PRODUCT_WRITE = "product:write"
    PRODUCT_SYNC = "product:sync"
    
    # 报告访问
    REPORT_READ = "report:read"
    REPORT_DOWNLOAD = "report:download"
    
    # 推荐管理
    RECOMMENDATION_READ = "recommendation:read"
    RECOMMENDATION_OVERRIDE = "recommendation:override"


# 角色权限矩阵
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.ADMIN: set(Permission),  # 管理员拥有所有权限
    
    Role.OPERATOR: {
        Permission.USER_READ,
        Permission.CONFIG_READ,
        Permission.CONFIG_WRITE,
        Permission.CONFIG_DEPLOY,
        Permission.CONFIG_ROLLBACK,
        Permission.PRODUCT_READ,
        Permission.PRODUCT_WRITE,
        Permission.PRODUCT_SYNC,
        Permission.ANALYTICS_READ,
        Permission.RECOMMENDATION_READ,
    },
    
    Role.REVIEWER: {
        Permission.USER_READ,
        Permission.REVIEW_READ,
        Permission.REVIEW_WRITE,
        Permission.REPORT_READ,
        Permission.RECOMMENDATION_READ,
        Permission.RECOMMENDATION_OVERRIDE,
    },
    
    Role.ANALYST: {
        Permission.USER_READ,
        Permission.ANALYTICS_READ,
        Permission.ANALYTICS_EXPORT,
        Permission.RECOMMENDATION_READ,
    },
    
    Role.SUPPORT: {
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.REPORT_READ,
        Permission.RECOMMENDATION_READ,
    },
    
    Role.USER: {
        # 普通用户只能访问自己的资源，通过 IDOR 检查控制
    },
}


class RBACService:
    """RBAC 权限服务"""
    
    @staticmethod
    def get_role_permissions(role: Role) -> Set[Permission]:
        """获取角色的所有权限"""
        return ROLE_PERMISSIONS.get(role, set())
    
    @staticmethod
    def has_permission(role: Role, permission: Permission) -> bool:
        """检查角色是否拥有指定权限"""
        role_permissions = ROLE_PERMISSIONS.get(role, set())
        return permission in role_permissions
    
    @staticmethod
    def has_any_permission(role: Role, permissions: List[Permission]) -> bool:
        """检查角色是否拥有任一指定权限"""
        role_permissions = ROLE_PERMISSIONS.get(role, set())
        return any(p in role_permissions for p in permissions)
    
    @staticmethod
    def has_all_permissions(role: Role, permissions: List[Permission]) -> bool:
        """检查角色是否拥有所有指定权限"""
        role_permissions = ROLE_PERMISSIONS.get(role, set())
        return all(p in role_permissions for p in permissions)
    
    @staticmethod
    def check_permission(role: Role, permission: Permission) -> None:
        """检查权限，无权限时抛出异常"""
        if not RBACService.has_permission(role, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission.value} required"
            )


class IDORProtection:
    """IDOR 防护服务"""
    
    @staticmethod
    def check_resource_ownership(
        user_id: UUID,
        resource_owner_id: UUID,
        role: Role = Role.USER
    ) -> None:
        """
        检查资源所有权
        
        Args:
            user_id: 当前用户 ID
            resource_owner_id: 资源所有者 ID
            role: 用户角色
            
        Raises:
            HTTPException: 如果用户无权访问资源
        """
        # 管理员和审核员可以访问所有资源
        if role in (Role.ADMIN, Role.REVIEWER, Role.SUPPORT):
            return
        
        # 普通用户只能访问自己的资源
        if user_id != resource_owner_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You can only access your own resources"
            )
    
    @staticmethod
    def check_resource_access(
        user_id: UUID,
        resource_owner_id: Optional[UUID],
        role: Role,
        required_permission: Optional[Permission] = None
    ) -> None:
        """
        综合检查资源访问权限
        
        Args:
            user_id: 当前用户 ID
            resource_owner_id: 资源所有者 ID（可选）
            role: 用户角色
            required_permission: 所需权限（可选）
        """
        # 如果有特定权限要求，先检查权限
        if required_permission:
            if RBACService.has_permission(role, required_permission):
                return  # 有权限则允许访问
        
        # 否则检查资源所有权
        if resource_owner_id:
            IDORProtection.check_resource_ownership(user_id, resource_owner_id, role)


class PIIMasker:
    """PII 遮罩服务"""
    
    # 电话号码正则（支持多种格式）
    PHONE_PATTERN = re.compile(
        r'(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}'
    )
    
    # 邮箱正则
    EMAIL_PATTERN = re.compile(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    )
    
    @staticmethod
    def mask_phone(phone: str) -> str:
        """
        遮罩电话号码
        
        保留前3位和后2位，中间用 * 替代
        例如: 13812345678 -> 138****5678
        """
        if not phone:
            return phone
        
        # 移除非数字字符进行处理
        digits = re.sub(r'\D', '', phone)
        
        if len(digits) <= 5:
            return '*' * len(digits)
        
        # 保留前3位和后2位
        return digits[:3] + '*' * (len(digits) - 5) + digits[-2:]
    
    @staticmethod
    def mask_email(email: str) -> str:
        """
        遮罩邮箱地址
        
        保留首字母和 @ 后的域名，中间用 * 替代
        例如: john.doe@example.com -> j****@example.com
        """
        if not email or '@' not in email:
            return email
        
        local, domain = email.rsplit('@', 1)
        
        if len(local) <= 1:
            masked_local = '*'
        else:
            masked_local = local[0] + '*' * (len(local) - 1)
        
        return f"{masked_local}@{domain}"
    
    @staticmethod
    def mask_contact(contact: str, contact_type: str) -> str:
        """
        根据联络类型遮罩联络方式
        
        Args:
            contact: 联络方式
            contact_type: 联络类型 ("phone" 或 "email")
        """
        if contact_type == "phone":
            return PIIMasker.mask_phone(contact)
        elif contact_type == "email":
            return PIIMasker.mask_email(contact)
        return contact
    
    @staticmethod
    def mask_text(text: str) -> str:
        """
        遮罩文本中的所有 PII
        
        自动检测并遮罩电话号码和邮箱
        """
        if not text:
            return text
        
        # 遮罩邮箱
        def mask_email_match(match):
            return PIIMasker.mask_email(match.group(0))
        
        result = PIIMasker.EMAIL_PATTERN.sub(mask_email_match, text)
        
        # 遮罩电话
        def mask_phone_match(match):
            return PIIMasker.mask_phone(match.group(0))
        
        result = PIIMasker.PHONE_PATTERN.sub(mask_phone_match, result)
        
        return result
    
    @staticmethod
    def mask_dict(data: dict, fields_to_mask: Optional[List[str]] = None) -> dict:
        """
        遮罩字典中的 PII 字段
        
        Args:
            data: 要处理的字典
            fields_to_mask: 要遮罩的字段列表，默认为 ["contact", "phone", "email"]
        """
        if fields_to_mask is None:
            fields_to_mask = ["contact", "phone", "email", "ip_address"]
        
        result = data.copy()
        
        for field in fields_to_mask:
            if field in result and result[field]:
                value = result[field]
                if '@' in str(value):
                    result[field] = PIIMasker.mask_email(str(value))
                elif field in ("phone", "contact"):
                    result[field] = PIIMasker.mask_phone(str(value))
                elif field == "ip_address":
                    result[field] = PIIMasker.mask_ip(str(value))
        
        return result
    
    @staticmethod
    def mask_ip(ip: str) -> str:
        """
        遮罩 IP 地址
        
        IPv4: 保留前两段，后两段用 * 替代
        例如: 192.168.1.100 -> 192.168.*.*
        """
        if not ip:
            return ip
        
        parts = ip.split('.')
        if len(parts) == 4:  # IPv4
            return f"{parts[0]}.{parts[1]}.*.*"
        
        # IPv6 或其他格式，简单遮罩后半部分
        if ':' in ip:
            parts = ip.split(':')
            half = len(parts) // 2
            return ':'.join(parts[:half] + ['*'] * (len(parts) - half))
        
        return ip



class PresignedURLGenerator:
    """预签名 URL 生成器 - 用于安全的报告预览"""
    
    DEFAULT_EXPIRY_MINUTES = 15
    
    @staticmethod
    def generate_preview_url(
        s3_key: str,
        bucket_name: str,
        s3_client,
        expiry_minutes: int = DEFAULT_EXPIRY_MINUTES
    ) -> dict:
        """
        生成短效预签名预览 URL
        
        Args:
            s3_key: S3 对象键
            bucket_name: S3 桶名
            s3_client: S3 客户端
            expiry_minutes: 过期时间（分钟），默认 15 分钟
            
        Returns:
            dict: 包含 url 和 expires_at
        """
        expiry_seconds = expiry_minutes * 60
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
        
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': s3_key,
            },
            ExpiresIn=expiry_seconds,
        )
        
        return {
            "url": url,
            "expires_at": expires_at,
            "expiry_minutes": expiry_minutes,
        }
    
    @staticmethod
    def validate_expiry(expiry_minutes: int) -> int:
        """
        验证并限制过期时间
        
        最大允许 15 分钟
        """
        max_expiry = 15
        if expiry_minutes > max_expiry:
            return max_expiry
        if expiry_minutes < 1:
            return 1
        return expiry_minutes


class SecurityContext(BaseModel):
    """安全上下文 - 包含当前请求的安全信息"""
    user_id: UUID
    role: Role
    permissions: Set[Permission] = set()
    ip_address: str = ""
    
    class Config:
        arbitrary_types_allowed = True
    
    def has_permission(self, permission: Permission) -> bool:
        """检查是否有指定权限"""
        return permission in self.permissions
    
    def check_permission(self, permission: Permission) -> None:
        """检查权限，无权限时抛出异常"""
        if not self.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission.value} required"
            )
    
    def can_access_resource(self, resource_owner_id: UUID) -> bool:
        """检查是否可以访问指定资源"""
        # 管理员、审核员、客服可以访问所有资源
        if self.role in (Role.ADMIN, Role.REVIEWER, Role.SUPPORT):
            return True
        # 其他用户只能访问自己的资源
        return self.user_id == resource_owner_id


def mask_pii(value: str, pii_type: str) -> str:
    """
    便捷函数：遮罩 PII 数据
    
    Args:
        value: 要遮罩的值
        pii_type: PII 类型 ("phone", "email", "ip")
        
    Returns:
        遮罩后的值
    """
    if pii_type == "phone":
        return PIIMasker.mask_phone(value)
    elif pii_type == "email":
        return PIIMasker.mask_email(value)
    elif pii_type == "ip":
        return PIIMasker.mask_ip(value)
    else:
        return PIIMasker.mask_text(value)


def require_permission(*permissions: Permission):
    """
    权限检查装饰器
    
    用于 FastAPI 路由函数，检查用户是否有指定权限
    
    Usage:
        @router.get("/admin/users")
        @require_permission(Permission.USER_READ)
        async def list_users(security_ctx: SecurityContext = Depends(get_security_context)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从 kwargs 中获取 security_context
            security_ctx = kwargs.get('security_ctx') or kwargs.get('security_context')
            
            if not security_ctx:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
            
            # 检查是否有任一所需权限
            has_perm = any(
                security_ctx.has_permission(p) for p in permissions
            )
            
            if not has_perm:
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: one of {[p.value for p in permissions]} required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
