"""IP Allowlist 白名单管理 API

管理允许访问管理后台的 IP 地址
"""

from datetime import datetime
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.admin import AdminUser, UserRole
from app.api.admin import get_current_admin, require_role

router = APIRouter(prefix="/api/admin/ip-allowlist", tags=["ip_allowlist"])

# 内存中存储 IP 白名单（生产环境应使用数据库）
# 格式: {"ip": {...metadata}}
ip_allowlist: dict = {}


class IPAllowlistEntry(BaseModel):
    """IP 白名单条目"""
    ip: str = Field(..., description="IP 地址或 CIDR")
    description: Optional[str] = None
    added_by: Optional[str] = None
    added_at: Optional[datetime] = None


class IPAllowlistResponse(BaseModel):
    """IP 白名单列表响应"""
    entries: List[IPAllowlistEntry]
    total: int
    enabled: bool


class AddIPRequest(BaseModel):
    """添加 IP 请求"""
    ip: str = Field(..., description="IP 地址或 CIDR（如 192.168.1.0/24）")
    description: Optional[str] = None


def is_ip_in_cidr(ip: str, cidr: str) -> bool:
    """检查 IP 是否在 CIDR 范围内
    
    简化实现，生产环境应使用 ipaddress 模块
    """
    if "/" not in cidr:
        return ip == cidr
    
    try:
        import ipaddress
        network = ipaddress.ip_network(cidr, strict=False)
        return ipaddress.ip_address(ip) in network
    except:
        return ip == cidr.split("/")[0]


def check_ip_allowed(ip: str) -> bool:
    """检查 IP 是否在白名单中"""
    if not ip_allowlist:
        # 白名单为空时允许所有 IP
        return True
    
    for allowed_ip in ip_allowlist.keys():
        if is_ip_in_cidr(ip, allowed_ip):
            return True
    
    return False


@router.get("", response_model=IPAllowlistResponse)
async def list_ip_allowlist(
    admin: AdminUser = Depends(require_role(UserRole.SUPER_ADMIN)),
):
    """
    获取 IP 白名单列表
    
    仅超级管理员可访问
    """
    entries = [
        IPAllowlistEntry(
            ip=ip,
            description=data.get("description"),
            added_by=data.get("added_by"),
            added_at=data.get("added_at")
        )
        for ip, data in ip_allowlist.items()
    ]
    
    return IPAllowlistResponse(
        entries=entries,
        total=len(entries),
        enabled=len(ip_allowlist) > 0
    )


@router.post("")
async def add_ip_to_allowlist(
    request: AddIPRequest,
    admin: AdminUser = Depends(require_role(UserRole.SUPER_ADMIN)),
):
    """
    添加 IP 到白名单
    
    支持单个 IP 或 CIDR 格式
    """
    if request.ip in ip_allowlist:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"IP {request.ip} 已存在"
        )
    
    ip_allowlist[request.ip] = {
        "description": request.description,
        "added_by": admin.username,
        "added_at": datetime.utcnow()
    }
    
    return {
        "message": f"IP {request.ip} 已添加到白名單",
        "total": len(ip_allowlist)
    }


@router.delete("/{ip}")
async def remove_ip_from_allowlist(
    ip: str,
    admin: AdminUser = Depends(require_role(UserRole.SUPER_ADMIN)),
):
    """
    从白名单移除 IP
    """
    # URL 编码处理
    ip = ip.replace("%2F", "/")
    
    if ip not in ip_allowlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IP {ip} 不在白名單中"
        )
    
    del ip_allowlist[ip]
    
    return {
        "message": f"IP {ip} 已從白名單移除",
        "total": len(ip_allowlist)
    }


@router.get("/check/{ip}")
async def check_ip_status(
    ip: str,
    admin: AdminUser = Depends(require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    """
    检查 IP 是否在白名单中
    """
    ip = ip.replace("%2F", "/")
    allowed = check_ip_allowed(ip)
    
    return {
        "ip": ip,
        "allowed": allowed,
        "allowlist_enabled": len(ip_allowlist) > 0
    }


@router.post("/clear")
async def clear_allowlist(
    admin: AdminUser = Depends(require_role(UserRole.SUPER_ADMIN)),
):
    """
    清空白名单（禁用 IP 限制）
    """
    ip_allowlist.clear()
    
    return {
        "message": "白名單已清空，IP 限制已禁用",
        "total": 0
    }
