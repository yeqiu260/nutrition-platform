"""Affiliate 链接追踪 API

实现 /out 重定向路由，记录点击事件并重定向到商品购买链接
"""

import uuid
from datetime import datetime, date
from typing import Optional
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth_deps import get_optional_user_id
from app.models.product import Product
from app.models.analytics import AnalyticsEvent

router = APIRouter(tags=["affiliate"])


def get_client_ip(request: Request) -> str:
    """获取客户端 IP 地址"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def add_utm_params(url: str, utm_source: str = "wysikhealth", 
                   utm_medium: str = "affiliate", 
                   click_id: Optional[str] = None) -> str:
    """添加 UTM 追踪参数到 URL"""
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    # 添加 UTM 参数
    query_params["utm_source"] = [utm_source]
    query_params["utm_medium"] = [utm_medium]
    query_params["utm_campaign"] = ["recommendation"]
    
    if click_id:
        query_params["click_id"] = [click_id]
    
    # 重建 URL
    new_query = urlencode(query_params, doseq=True)
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))


@router.get("/out/{product_id}")
async def affiliate_redirect(
    product_id: str,
    request: Request,
    session_id: Optional[str] = Query(None, description="推荐会话 ID"),
    db: AsyncSession = Depends(get_db),
    user_id: Optional[uuid.UUID] = Depends(get_optional_user_id),
):
    """
    Affiliate 重定向路由
    
    记录点击事件后重定向到商品购买链接
    支持匿名用户和已登录用户
    """
    # 获取商品
    try:
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="無效的商品 ID")
    
    result = await db.execute(
        select(Product).where(
            Product.id == product_uuid,
            Product.is_active == True,
            Product.is_approved == True
        )
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在或已下架")
    
    # 检查 Cap 限制
    cap_check = await check_click_cap(db, product)
    if not cap_check["allowed"]:
        raise HTTPException(
            status_code=429, 
            detail=f"該商品已達到點擊上限: {cap_check['reason']}"
        )
    
    # 检查地区限制
    client_ip = get_client_ip(request)
    region_check = await check_region_restriction(product, client_ip)
    if not region_check["allowed"]:
        raise HTTPException(
            status_code=403,
            detail=f"該商品在您的地區不可用: {region_check['user_region']}"
        )
    
    # 生成 click_id
    click_id = str(uuid.uuid4())
    
    # 记录点击事件
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")
    
    event = AnalyticsEvent(
        user_id=user_id or uuid.UUID("00000000-0000-0000-0000-000000000000"),  # 匿名用户使用固定 ID
        session_id=uuid.UUID(session_id) if session_id else None,
        event_type="product_clicked",
        event_data={
            "product_id": str(product.id),
            "product_name": product.name,
            "partner_id": str(product.partner_id),
            "partner_name": product.partner_name,
            "click_id": click_id,
            "redirect_url": product.purchase_url,
            "is_anonymous": user_id is None,
        },
        ip_address=client_ip,
        user_agent=user_agent,
    )
    db.add(event)
    
    # 更新点击统计
    await increment_click_count(db, product.id)
    
    await db.commit()
    
    # 添加 UTM 参数并重定向
    redirect_url = add_utm_params(
        product.purchase_url,
        click_id=click_id
    )
    
    return RedirectResponse(url=redirect_url, status_code=302)


async def check_click_cap(db: AsyncSession, product: Product) -> dict:
    """检查点击 Cap 限制"""
    # 如果商品没有设置 Cap，直接允许
    click_cap = getattr(product, 'click_cap', None)
    daily_cap = getattr(product, 'daily_cap', None)
    
    if not click_cap and not daily_cap:
        return {"allowed": True}
    
    # 获取总点击数
    if click_cap:
        result = await db.execute(
            select(func.count(AnalyticsEvent.id)).where(
                AnalyticsEvent.event_type == "product_clicked",
                AnalyticsEvent.event_data["product_id"].astext == str(product.id)
            )
        )
        total_clicks = result.scalar() or 0
        
        if total_clicks >= click_cap:
            return {"allowed": False, "reason": "總點擊上限已達到"}
    
    # 获取今日点击数
    if daily_cap:
        today = date.today()
        result = await db.execute(
            select(func.count(AnalyticsEvent.id)).where(
                AnalyticsEvent.event_type == "product_clicked",
                AnalyticsEvent.event_data["product_id"].astext == str(product.id),
                func.date(AnalyticsEvent.created_at) == today
            )
        )
        daily_clicks = result.scalar() or 0
        
        if daily_clicks >= daily_cap:
            return {"allowed": False, "reason": "每日點擊上限已達到"}
    
    return {"allowed": True}


async def check_region_restriction(product: Product, client_ip: str) -> dict:
    """检查地区限制
    
    使用简单的 IP 判断，生产环境应使用 MaxMind GeoIP 或类似服务
    """
    allowed_regions = getattr(product, 'allowed_regions', None)
    
    # 如果没有设置地区限制，允许所有
    if not allowed_regions:
        return {"allowed": True, "user_region": "ALL"}
    
    # 简单的地区检测（生产环境应使用 GeoIP 服务）
    user_region = detect_region_from_ip(client_ip)
    
    if user_region in allowed_regions or user_region == "UNKNOWN":
        return {"allowed": True, "user_region": user_region}
    
    return {"allowed": False, "user_region": user_region, "allowed_regions": allowed_regions}


def detect_region_from_ip(ip: str) -> str:
    """从 IP 地址检测地区代码
    
    简化实现，生产环境应使用 MaxMind GeoLite2 或 ip-api.com
    """
    # 简单的 IP 前缀判断（仅作示例）
    # 台湾常见 IP 段：36.224-36.239, 61.216-61.223, 114.24-114.47
    # 香港常见 IP 段：14., 43., 58., 59., 101., 203.
    
    if ip.startswith(("36.22", "36.23", "61.21", "61.22", "114.2", "114.3", "114.4")):
        return "TW"
    elif ip.startswith(("14.", "43.", "58.", "59.", "101.", "203.")):
        return "HK"
    elif ip.startswith(("127.", "192.168.", "10.", "172.")):
        return "LOCAL"  # 本地/私有 IP
    
    return "UNKNOWN"


async def increment_click_count(db: AsyncSession, product_id: uuid.UUID):
    """增加点击计数（用于快速统计）"""
    # 这里使用 event_data 记录，也可以创建单独的统计表
    pass


@router.get("/out/{product_id}/stats")
async def get_product_click_stats(
    product_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取商品点击统计"""
    try:
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="無效的商品 ID")
    
    # 总点击数
    result = await db.execute(
        select(func.count(AnalyticsEvent.id)).where(
            AnalyticsEvent.event_type == "product_clicked",
            AnalyticsEvent.event_data["product_id"].astext == str(product_uuid)
        )
    )
    total_clicks = result.scalar() or 0
    
    # 今日点击数
    today = date.today()
    result = await db.execute(
        select(func.count(AnalyticsEvent.id)).where(
            AnalyticsEvent.event_type == "product_clicked",
            AnalyticsEvent.event_data["product_id"].astext == str(product_uuid),
            func.date(AnalyticsEvent.created_at) == today
        )
    )
    daily_clicks = result.scalar() or 0
    
    return {
        "product_id": product_id,
        "total_clicks": total_clicks,
        "daily_clicks": daily_clicks,
        "date": today.isoformat()
    }
