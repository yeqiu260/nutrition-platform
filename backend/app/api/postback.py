"""转化回调 API (Postback)

接收来自合作商的订单转化通知，关联到原始点击事件
"""

import logging
from datetime import datetime
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.analytics import AnalyticsEvent

router = APIRouter(prefix="/api/postback", tags=["postback"])
logger = logging.getLogger(__name__)


class PostbackRequest(BaseModel):
    """转化回调请求"""
    click_id: str  # 对应 affiliate 重定向时生成的 click_id
    order_id: str  # 合作商订单 ID
    amount: float  # 订单金额
    currency: str = "TWD"
    status: str = "completed"  # completed | pending | cancelled
    commission: Optional[float] = None  # 佣金金额


class PostbackResponse(BaseModel):
    """转化回调响应"""
    success: bool
    message: str
    conversion_id: Optional[str] = None


@router.get("")
@router.post("")
async def receive_postback(
    request: Request,
    click_id: str = Query(..., description="点击 ID"),
    order_id: str = Query(..., description="订单 ID"),
    amount: float = Query(..., description="订单金额"),
    currency: str = Query("TWD", description="货币"),
    status: str = Query("completed", description="订单状态"),
    db: AsyncSession = Depends(get_db),
) -> PostbackResponse:
    """
    接收转化回调
    
    支持 GET 和 POST 请求，以兼容不同合作商的回调机制
    
    参数通过 Query 或 Body 传入
    """
    # 查找原始点击事件
    result = await db.execute(
        select(AnalyticsEvent).where(
            AnalyticsEvent.event_type == "product_clicked",
            AnalyticsEvent.event_data["click_id"].astext == click_id
        )
    )
    click_event = result.scalar_one_or_none()
    
    if not click_event:
        logger.warning(f"Postback received for unknown click_id: {click_id}")
        return PostbackResponse(
            success=False,
            message=f"Unknown click_id: {click_id}"
        )
    
    # 创建转化事件
    conversion_id = str(uuid.uuid4())
    conversion_event = AnalyticsEvent(
        user_id=click_event.user_id,
        session_id=click_event.session_id,
        event_type="purchase_completed",
        event_data={
            "conversion_id": conversion_id,
            "click_id": click_id,
            "order_id": order_id,
            "amount": amount,
            "currency": currency,
            "status": status,
            "product_id": click_event.event_data.get("product_id"),
            "partner_id": click_event.event_data.get("partner_id"),
            "partner_name": click_event.event_data.get("partner_name"),
        },
        ip_address=request.client.host if request.client else None,
    )
    db.add(conversion_event)
    await db.commit()
    
    logger.info(f"Conversion recorded: click_id={click_id}, order_id={order_id}, amount={amount}")
    
    return PostbackResponse(
        success=True,
        message="Conversion recorded successfully",
        conversion_id=conversion_id
    )


@router.get("/stats")
async def get_conversion_stats(
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    partner_id: Optional[str] = Query(None, description="合作商 ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取转化统计
    
    返回点击数、转化数、转化率、总金额等指标
    """
    from sqlalchemy import func
    
    # 基础查询条件
    click_query = select(func.count(AnalyticsEvent.id)).where(
        AnalyticsEvent.event_type == "product_clicked"
    )
    conversion_query = select(
        func.count(AnalyticsEvent.id),
        func.sum(AnalyticsEvent.event_data["amount"].astext.cast(type_=func.numeric))
    ).where(
        AnalyticsEvent.event_type == "purchase_completed"
    )
    
    # 合作商过滤
    if partner_id:
        click_query = click_query.where(
            AnalyticsEvent.event_data["partner_id"].astext == partner_id
        )
        conversion_query = conversion_query.where(
            AnalyticsEvent.event_data["partner_id"].astext == partner_id
        )
    
    # 执行查询
    click_result = await db.execute(click_query)
    total_clicks = click_result.scalar() or 0
    
    conversion_result = await db.execute(conversion_query)
    row = conversion_result.one()
    total_conversions = row[0] or 0
    total_revenue = float(row[1]) if row[1] else 0.0
    
    # 计算转化率
    conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0.0
    
    return {
        "total_clicks": total_clicks,
        "total_conversions": total_conversions,
        "conversion_rate": round(conversion_rate, 2),
        "total_revenue": round(total_revenue, 2),
        "currency": "TWD",
        "period": {
            "start_date": start_date,
            "end_date": end_date,
        }
    }
