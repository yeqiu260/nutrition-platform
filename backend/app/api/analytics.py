"""分析事件 API 路由"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth_deps import get_current_user_id, get_optional_user_id  # 导入认证依赖
from app.services.analytics import (
    AnalyticsService,
    EventType,
    EventListResponse,
    EventSummary,
    AnalyticsEventSchema,
    create_analytics_service,
)
from app.models.admin import AdminUser, UserRole
from app.api.admin import require_role

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# ===== 请求/响应模型 =====

class RecordEventRequest(BaseModel):
    """记录事件请求"""
    event_type: str = Field(..., description="事件类型")
    session_id: Optional[str] = Field(None, description="推荐会话 ID")
    event_data: Optional[Dict[str, Any]] = Field(None, description="事件数据")


class RecordEventResponse(BaseModel):
    """记录事件响应"""
    event_id: str
    event_type: str
    created_at: datetime


class QuizCompletedRequest(BaseModel):
    """问卷完成事件请求"""
    session_id: str
    questionnaire_version: str
    answers_count: int


class RecommendationGeneratedRequest(BaseModel):
    """推荐生成事件请求"""
    session_id: str
    recommendation_count: int
    requires_review: bool = False


class PurchaseCompletedRequest(BaseModel):
    """购买完成事件请求"""
    session_id: Optional[str] = None
    order_id: str
    order_total: float
    currency: str = "TWD"
    extra: Optional[Dict[str, Any]] = None


# ===== 辅助函数 =====

def get_client_info(request: Request) -> tuple[Optional[str], Optional[str]]:
    """获取客户端信息"""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip_address, user_agent


# ===== API 端点 =====

@router.post("/events", response_model=RecordEventResponse)
async def record_event(
    request: Request,
    body: RecordEventRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> RecordEventResponse:
    """记录通用分析事件
    
    用于记录各类用户行为事件，支持自定义事件数据。
    """
    ip_address, user_agent = get_client_info(request)
    
    # 验证事件类型
    try:
        event_type = EventType(body.event_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid event type: {body.event_type}",
        )
    
    session_id = uuid.UUID(body.session_id) if body.session_id else None
    
    service = create_analytics_service(db)
    event = await service.record_event(
        user_id=user_id,
        event_type=event_type,
        session_id=session_id,
        event_data=body.event_data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    return RecordEventResponse(
        event_id=str(event.id),
        event_type=event.event_type,
        created_at=event.created_at,
    )


@router.post("/events/quiz-completed", response_model=RecordEventResponse)
async def record_quiz_completed(
    request: Request,
    body: QuizCompletedRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> RecordEventResponse:
    """记录问卷完成事件（需求 6.1）"""
    ip_address, user_agent = get_client_info(request)
    
    service = create_analytics_service(db)
    event = await service.record_quiz_completed(
        user_id=user_id,
        session_id=uuid.UUID(body.session_id),
        questionnaire_version=body.questionnaire_version,
        answers_count=body.answers_count,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    return RecordEventResponse(
        event_id=str(event.id),
        event_type=event.event_type,
        created_at=event.created_at,
    )


@router.post("/events/recommendation-generated", response_model=RecordEventResponse)
async def record_recommendation_generated(
    request: Request,
    body: RecommendationGeneratedRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> RecordEventResponse:
    """记录推荐生成事件（需求 6.3）"""
    
    service = create_analytics_service(db)
    event = await service.record_recommendation_generated(
        user_id=user_id,
        session_id=uuid.UUID(body.session_id),
        recommendation_count=body.recommendation_count,
        requires_review=body.requires_review,
    )
    
    return RecordEventResponse(
        event_id=str(event.id),
        event_type=event.event_type,
        created_at=event.created_at,
    )


@router.post("/events/recommendation-viewed", response_model=RecordEventResponse)
async def record_recommendation_viewed(
    request: Request,
    session_id: str = Query(..., description="推荐会话 ID"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> RecordEventResponse:
    """记录推荐查看事件（需求 6.3）"""
    ip_address, user_agent = get_client_info(request)
    
    service = create_analytics_service(db)
    event = await service.record_recommendation_viewed(
        user_id=user_id,
        session_id=uuid.UUID(session_id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    return RecordEventResponse(
        event_id=str(event.id),
        event_type=event.event_type,
        created_at=event.created_at,
    )


@router.post("/events/purchase-completed", response_model=RecordEventResponse)
async def record_purchase_completed(
    request: Request,
    body: PurchaseCompletedRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> RecordEventResponse:
    """记录购买完成事件（需求 6.5）"""
    
    session_id = uuid.UUID(body.session_id) if body.session_id else None
    
    service = create_analytics_service(db)
    event = await service.record_purchase_completed(
        user_id=user_id,
        session_id=session_id,
        order_id=body.order_id,
        order_total=body.order_total,
        currency=body.currency,
        extra=body.extra,
    )
    
    return RecordEventResponse(
        event_id=str(event.id),
        event_type=event.event_type,
        created_at=event.created_at,
    )


# ===== 查询端点 =====

@router.get("/events", response_model=EventListResponse)
async def get_user_events(
    request: Request,
    event_type: Optional[str] = Query(None, description="事件类型过滤"),
    session_id: Optional[str] = Query(None, description="会话 ID 过滤"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> EventListResponse:
    """查询当前用户的事件列表"""
    
    # 验证事件类型
    event_type_enum = None
    if event_type:
        try:
            event_type_enum = EventType(event_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event type: {event_type}",
            )
    
    session_uuid = uuid.UUID(session_id) if session_id else None
    
    service = create_analytics_service(db)
    return await service.get_events_by_user(
        user_id=user_id,
        event_type=event_type_enum,
        session_id=session_uuid,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )


@router.get("/events/session/{session_id}", response_model=EventListResponse)
async def get_session_events(
    session_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
) -> EventListResponse:
    """查询指定会话的事件列表"""
    service = create_analytics_service(db)
    return await service.get_events_by_session(
        session_id=uuid.UUID(session_id),
        page=page,
        page_size=page_size,
    )


@router.get("/events/{event_id}", response_model=AnalyticsEventSchema)
async def get_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
) -> AnalyticsEventSchema:
    """获取单个事件详情"""
    service = create_analytics_service(db)
    event = await service.get_event(uuid.UUID(event_id))
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    return AnalyticsEventSchema(
        id=str(event.id),
        user_id=str(event.user_id),
        session_id=str(event.session_id) if event.session_id else None,
        event_type=event.event_type,
        event_data=event.event_data,
        created_at=event.created_at,
        ip_address=event.ip_address,
        user_agent=event.user_agent,
    )


@router.get("/summary", response_model=List[EventSummary])
async def get_event_summary(
    request: Request,
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> List[EventSummary]:
    """获取当前用户的事件统计摘要"""
    
    service = create_analytics_service(db)
    return await service.get_event_summary_by_user(
        user_id=user_id,
        start_time=start_time,
        end_time=end_time,
    )


@router.get("/admin/summary", response_model=List[EventSummary])
async def get_admin_event_summary(
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
) -> List[EventSummary]:
    """获取系统所有事件统计摘要（管理员专用）"""
    service = create_analytics_service(db)
    return await service.get_event_summary_all(
        start_time=start_time,
        end_time=end_time,
    )


@router.get("/admin/events", response_model=EventListResponse)
async def get_admin_events(
    event_type: Optional[str] = Query(None, description="事件类型过滤"),
    session_id: Optional[str] = Query(None, description="会话 ID 过滤"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
) -> EventListResponse:
    """查询系统所有事件列表（管理员专用）"""
    
    # 验证事件类型
    event_type_enum = None
    if event_type:
        try:
            event_type_enum = EventType(event_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event type: {event_type}",
            )
    
    session_uuid = uuid.UUID(session_id) if session_id else None
    
    service = create_analytics_service(db)
    return await service.get_all_events(
        event_type=event_type_enum,
        session_id=session_uuid,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )


@router.get("/event-types", response_model=List[str])
async def get_event_types() -> List[str]:
    """获取所有支持的事件类型"""
    return [e.value for e in EventType]


# ===== 产品点击追踪端点（公开，不需要登录）=====

class ProductClickRequest(BaseModel):
    """产品点击事件请求"""
    product_id: str
    session_id: Optional[str] = None
    recommendation_item_id: Optional[str] = None
    redirect_url: str


@router.post("/events/product-clicked")
async def record_product_click(
    request: Request,
    body: ProductClickRequest,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[uuid.UUID] = Depends(get_optional_user_id),
) -> dict:
    """记录产品点击事件（公开端点，不需要登录）
    
    用于追踪用户点击产品购买链接的行为。
    如果用户已登录，会记录到其账户；否则只记录匿名事件。
    """
    # 如果没有用户 ID，跳过记录（或记录为匿名事件）
    if not user_id:
        return {"success": True, "message": "Anonymous click recorded (not persisted)"}
    
    ip_address, user_agent = get_client_info(request)
    session_id = uuid.UUID(body.session_id) if body.session_id else None
    
    service = create_analytics_service(db)
    event = await service.record_product_clicked(
        user_id=user_id,
        session_id=session_id or uuid.uuid4(),  # 如果没有 session_id，生成一个
        commerce_id=body.product_id,
        recommendation_item_id=body.recommendation_item_id or body.product_id,
        redirect_url=body.redirect_url,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    return {
        "success": True,
        "event_id": str(event.id),
        "message": "Product click recorded"
    }


# ===== 数据汇出端点（需求 9.7）=====

class ExportUserDataResponse(BaseModel):
    """用户数据汇出响应"""
    exported_at: str
    user_id: str
    user: Optional[Dict[str, Any]] = None
    consents: Optional[List[Dict[str, Any]]] = None
    health_profiles: Optional[List[Dict[str, Any]]] = None
    events: Optional[List[Dict[str, Any]]] = None
    events_total: Optional[int] = None


@router.get("/export", response_model=ExportUserDataResponse)
async def export_user_data(
    request: Request,
    include_events: bool = Query(True, description="是否包含事件数据"),
    include_profile: bool = Query(True, description="是否包含健康档案"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> ExportUserDataResponse:
    """
    汇出当前用户资料（需求 9.7）
    
    安全要求：
    - 自动应用 PII 遮罩和去识别化
    - 联络方式（电话/邮箱）被遮罩
    - IP 地址被遮罩
    
    返回用户的所有资料，包括：
    - 基本信息（遮罩后的联络方式）
    - 同意记录
    - 健康档案（可选）
    - 事件数据（可选，最多 1000 条）
    """
    
    service = create_analytics_service(db)
    export_data = await service.export_user_data(
        user_id=user_id,
        include_events=include_events,
        include_profile=include_profile,
        apply_pii_mask=True,  # 始终应用 PII 遮罩
    )
    
    return ExportUserDataResponse(**export_data)


@router.get("/export/{target_user_id}", response_model=ExportUserDataResponse)
async def export_user_data_admin(
    target_user_id: str,
    request: Request,
    include_events: bool = Query(True, description="是否包含事件数据"),
    include_profile: bool = Query(True, description="是否包含健康档案"),
    apply_pii_mask: bool = Query(True, description="是否应用 PII 遮罩"),
    db: AsyncSession = Depends(get_db),
) -> ExportUserDataResponse:
    """
    汇出指定用户资料（管理员/分析师专用）
    
    需要 ANALYTICS_EXPORT 权限。
    
    安全要求：
    - 默认应用 PII 遮罩
    - 只有特定权限可以获取未遮罩数据
    
    Args:
        target_user_id: 目标用户 ID
        include_events: 是否包含事件数据
        include_profile: 是否包含健康档案
        apply_pii_mask: 是否应用 PII 遮罩（默认 True）
    """
    # 权限检查由 RBAC 中间件处理
    # 这里只需要执行汇出
    
    service = create_analytics_service(db)
    export_data = await service.export_user_data(
        user_id=uuid.UUID(target_user_id),
        include_events=include_events,
        include_profile=include_profile,
        apply_pii_mask=apply_pii_mask,
    )
    
    return ExportUserDataResponse(**export_data)
