"""分析事件追踪服务模块"""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional, Any, Dict

from pydantic import BaseModel, Field
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AnalyticsEvent


class EventType(str, Enum):
    """事件类型枚举
    
    根据需求 6.1-6.5 定义的事件类型：
    - 问卷完成事件
    - 报告上载和抽取成功/失败事件
    - 推荐生成和查看事件
    - 商品点击和合作商 Offer 点击事件
    - 购买回传事件
    """
    # 问卷相关
    QUIZ_STARTED = "quiz_started"
    QUIZ_COMPLETED = "quiz_completed"
    
    # 报告相关
    REPORT_UPLOADED = "report_uploaded"
    REPORT_EXTRACTION_STARTED = "report_extraction_started"
    REPORT_EXTRACTED = "report_extracted"
    REPORT_EXTRACTION_FAILED = "report_extraction_failed"
    
    # 推荐相关
    RECOMMENDATION_GENERATED = "recommendation_generated"
    RECOMMENDATION_VIEWED = "recommendation_viewed"
    
    # 商业相关
    PRODUCT_CLICKED = "product_clicked"
    OFFER_CLICKED = "offer_clicked"
    PURCHASE_COMPLETED = "purchase_completed"
    
    # 用户行为
    USER_LOGIN = "user_login"
    CONSENT_GIVEN = "consent_given"


class EventDataSchema(BaseModel):
    """事件数据 Schema"""
    # 通用字段
    source: Optional[str] = None  # web | mobile | api
    
    # 问卷相关
    questionnaire_version: Optional[str] = None
    answers_count: Optional[int] = None
    
    # 报告相关
    report_id: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    extraction_method: Optional[str] = None  # llm | ocr
    error_message: Optional[str] = None
    metrics_count: Optional[int] = None
    
    # 推荐相关
    recommendation_count: Optional[int] = None
    requires_review: Optional[bool] = None
    
    # 商业相关
    slot_type: Optional[str] = None
    commerce_id: Optional[str] = None
    recommendation_item_id: Optional[str] = None
    redirect_url: Optional[str] = None
    
    # 购买相关
    order_id: Optional[str] = None
    order_total: Optional[float] = None
    currency: Optional[str] = None
    
    # 额外数据
    extra: Optional[Dict[str, Any]] = None


class AnalyticsEventSchema(BaseModel):
    """分析事件 Schema"""
    id: str
    user_id: str
    session_id: Optional[str] = None
    event_type: str
    event_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class EventListResponse(BaseModel):
    """事件列表响应"""
    events: List[AnalyticsEventSchema]
    total: int
    page: int
    page_size: int
    has_more: bool


class EventSummary(BaseModel):
    """事件统计摘要"""
    event_type: str
    count: int
    first_at: Optional[datetime] = None
    last_at: Optional[datetime] = None


class AnalyticsService:
    """分析事件追踪服务
    
    实现需求 6：事件追踪
    - 6.1 追踪问卷完成事件
    - 6.2 追踪报告上载和抽取成功/失败事件
    - 6.3 追踪推荐生成和查看事件
    - 6.4 追踪商品点击和合作商 Offer 点击事件
    - 6.5 记录购买回传事件
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_event(
        self,
        user_id: uuid.UUID,
        event_type: EventType,
        session_id: Optional[uuid.UUID] = None,
        event_data: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AnalyticsEvent:
        """记录分析事件
        
        Args:
            user_id: 用户 ID
            event_type: 事件类型
            session_id: 推荐会话 ID（可选）
            event_data: 事件数据（可选）
            ip_address: IP 地址（可选）
            user_agent: User Agent（可选）
            
        Returns:
            创建的事件记录
        """
        event = AnalyticsEvent(
            user_id=user_id,
            session_id=session_id,
            event_type=event_type.value,
            event_data=event_data,
            created_at=datetime.utcnow(),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event


    # ===== 便捷方法：问卷事件 =====

    async def record_quiz_started(
        self,
        user_id: uuid.UUID,
        questionnaire_version: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AnalyticsEvent:
        """记录问卷开始事件"""
        return await self.record_event(
            user_id=user_id,
            event_type=EventType.QUIZ_STARTED,
            event_data={"questionnaire_version": questionnaire_version},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def record_quiz_completed(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        questionnaire_version: str,
        answers_count: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AnalyticsEvent:
        """记录问卷完成事件（需求 6.1）"""
        return await self.record_event(
            user_id=user_id,
            event_type=EventType.QUIZ_COMPLETED,
            session_id=session_id,
            event_data={
                "questionnaire_version": questionnaire_version,
                "answers_count": answers_count,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    # ===== 便捷方法：报告事件 =====

    async def record_report_uploaded(
        self,
        user_id: uuid.UUID,
        report_id: str,
        file_type: str,
        file_size: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AnalyticsEvent:
        """记录报告上载事件（需求 6.2）"""
        return await self.record_event(
            user_id=user_id,
            event_type=EventType.REPORT_UPLOADED,
            event_data={
                "report_id": report_id,
                "file_type": file_type,
                "file_size": file_size,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def record_report_extraction_started(
        self,
        user_id: uuid.UUID,
        report_id: str,
        extraction_method: str = "llm",
    ) -> AnalyticsEvent:
        """记录报告抽取开始事件"""
        return await self.record_event(
            user_id=user_id,
            event_type=EventType.REPORT_EXTRACTION_STARTED,
            event_data={
                "report_id": report_id,
                "extraction_method": extraction_method,
            },
        )

    async def record_report_extracted(
        self,
        user_id: uuid.UUID,
        report_id: str,
        extraction_method: str,
        metrics_count: int,
    ) -> AnalyticsEvent:
        """记录报告抽取成功事件（需求 6.2）"""
        return await self.record_event(
            user_id=user_id,
            event_type=EventType.REPORT_EXTRACTED,
            event_data={
                "report_id": report_id,
                "extraction_method": extraction_method,
                "metrics_count": metrics_count,
            },
        )

    async def record_report_extraction_failed(
        self,
        user_id: uuid.UUID,
        report_id: str,
        error_message: str,
        extraction_method: str = "llm",
    ) -> AnalyticsEvent:
        """记录报告抽取失败事件（需求 6.2）"""
        return await self.record_event(
            user_id=user_id,
            event_type=EventType.REPORT_EXTRACTION_FAILED,
            event_data={
                "report_id": report_id,
                "extraction_method": extraction_method,
                "error_message": error_message,
            },
        )

    # ===== 便捷方法：推荐事件 =====

    async def record_recommendation_generated(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        recommendation_count: int,
        requires_review: bool,
    ) -> AnalyticsEvent:
        """记录推荐生成事件（需求 6.3）"""
        return await self.record_event(
            user_id=user_id,
            event_type=EventType.RECOMMENDATION_GENERATED,
            session_id=session_id,
            event_data={
                "recommendation_count": recommendation_count,
                "requires_review": requires_review,
            },
        )

    async def record_recommendation_viewed(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AnalyticsEvent:
        """记录推荐查看事件（需求 6.3）"""
        return await self.record_event(
            user_id=user_id,
            event_type=EventType.RECOMMENDATION_VIEWED,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    # ===== 便捷方法：商业事件 =====

    async def record_product_clicked(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        commerce_id: str,
        recommendation_item_id: str,
        redirect_url: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AnalyticsEvent:
        """记录商品点击事件（需求 6.4）"""
        return await self.record_event(
            user_id=user_id,
            event_type=EventType.PRODUCT_CLICKED,
            session_id=session_id,
            event_data={
                "slot_type": "shopify",
                "commerce_id": commerce_id,
                "recommendation_item_id": recommendation_item_id,
                "redirect_url": redirect_url,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def record_offer_clicked(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        commerce_id: str,
        recommendation_item_id: str,
        redirect_url: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AnalyticsEvent:
        """记录合作商 Offer 点击事件（需求 6.4）"""
        return await self.record_event(
            user_id=user_id,
            event_type=EventType.OFFER_CLICKED,
            session_id=session_id,
            event_data={
                "slot_type": "partner",
                "commerce_id": commerce_id,
                "recommendation_item_id": recommendation_item_id,
                "redirect_url": redirect_url,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def record_purchase_completed(
        self,
        user_id: uuid.UUID,
        session_id: Optional[uuid.UUID],
        order_id: str,
        order_total: float,
        currency: str = "TWD",
        extra: Optional[Dict[str, Any]] = None,
    ) -> AnalyticsEvent:
        """记录购买完成事件（需求 6.5）"""
        event_data = {
            "order_id": order_id,
            "order_total": order_total,
            "currency": currency,
        }
        if extra:
            event_data["extra"] = extra
            
        return await self.record_event(
            user_id=user_id,
            event_type=EventType.PURCHASE_COMPLETED,
            session_id=session_id,
            event_data=event_data,
        )


    # ===== 便捷方法：用户行为事件 =====

    async def record_user_login(
        self,
        user_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AnalyticsEvent:
        """记录用户登入事件"""
        return await self.record_event(
            user_id=user_id,
            event_type=EventType.USER_LOGIN,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def record_consent_given(
        self,
        user_id: uuid.UUID,
        consent_type: str,
        consent_version: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AnalyticsEvent:
        """记录同意授权事件"""
        return await self.record_event(
            user_id=user_id,
            event_type=EventType.CONSENT_GIVEN,
            event_data={
                "consent_type": consent_type,
                "consent_version": consent_version,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    # ===== 查询方法 =====

    async def get_event(self, event_id: uuid.UUID) -> Optional[AnalyticsEvent]:
        """获取单个事件"""
        stmt = select(AnalyticsEvent).where(AnalyticsEvent.id == event_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_events_by_user(
        self,
        user_id: uuid.UUID,
        event_type: Optional[EventType] = None,
        session_id: Optional[uuid.UUID] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> EventListResponse:
        """查询用户事件列表
        
        Args:
            user_id: 用户 ID
            event_type: 事件类型过滤（可选）
            session_id: 会话 ID 过滤（可选）
            start_time: 开始时间过滤（可选）
            end_time: 结束时间过滤（可选）
            page: 页码
            page_size: 每页数量
            
        Returns:
            事件列表响应
        """
        # 构建查询条件
        conditions = [AnalyticsEvent.user_id == user_id]
        
        if event_type:
            conditions.append(AnalyticsEvent.event_type == event_type.value)
        if session_id:
            conditions.append(AnalyticsEvent.session_id == session_id)
        if start_time:
            conditions.append(AnalyticsEvent.created_at >= start_time)
        if end_time:
            conditions.append(AnalyticsEvent.created_at <= end_time)

        # 查询总数
        count_stmt = select(AnalyticsEvent).where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = len(count_result.scalars().all())

        # 分页查询
        offset = (page - 1) * page_size
        stmt = (
            select(AnalyticsEvent)
            .where(and_(*conditions))
            .order_by(desc(AnalyticsEvent.created_at))
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        events = result.scalars().all()

        return EventListResponse(
            events=[
                AnalyticsEventSchema(
                    id=str(e.id),
                    user_id=str(e.user_id),
                    session_id=str(e.session_id) if e.session_id else None,
                    event_type=e.event_type,
                    event_data=e.event_data,
                    created_at=e.created_at,
                    ip_address=e.ip_address,
                    user_agent=e.user_agent,
                )
                for e in events
            ],
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + len(events)) < total,
        )

    async def get_events_by_session(
        self,
        session_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> EventListResponse:
        """查询会话事件列表"""
        # 查询总数
        count_stmt = select(AnalyticsEvent).where(
            AnalyticsEvent.session_id == session_id
        )
        count_result = await self.db.execute(count_stmt)
        total = len(count_result.scalars().all())

        # 分页查询
        offset = (page - 1) * page_size
        stmt = (
            select(AnalyticsEvent)
            .where(AnalyticsEvent.session_id == session_id)
            .order_by(desc(AnalyticsEvent.created_at))
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        events = result.scalars().all()

        return EventListResponse(
            events=[
                AnalyticsEventSchema(
                    id=str(e.id),
                    user_id=str(e.user_id),
                    session_id=str(e.session_id) if e.session_id else None,
                    event_type=e.event_type,
                    event_data=e.event_data,
                    created_at=e.created_at,
                    ip_address=e.ip_address,
                    user_agent=e.user_agent,
                )
                for e in events
            ],
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + len(events)) < total,
        )

    async def get_event_summary_by_user(
        self,
        user_id: uuid.UUID,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[EventSummary]:
        """获取用户事件统计摘要"""
        conditions = [AnalyticsEvent.user_id == user_id]
        if start_time:
            conditions.append(AnalyticsEvent.created_at >= start_time)
        if end_time:
            conditions.append(AnalyticsEvent.created_at <= end_time)

        stmt = select(AnalyticsEvent).where(and_(*conditions))
        result = await self.db.execute(stmt)
        events = result.scalars().all()

        # 按事件类型分组统计
        summary_dict: Dict[str, Dict[str, Any]] = {}
        for event in events:
            if event.event_type not in summary_dict:
                summary_dict[event.event_type] = {
                    "count": 0,
                    "first_at": event.created_at,
                    "last_at": event.created_at,
                }
            summary_dict[event.event_type]["count"] += 1
            if event.created_at < summary_dict[event.event_type]["first_at"]:
                summary_dict[event.event_type]["first_at"] = event.created_at
            if event.created_at > summary_dict[event.event_type]["last_at"]:
                summary_dict[event.event_type]["last_at"] = event.created_at

        return [
            EventSummary(
                event_type=event_type,
                count=data["count"],
                first_at=data["first_at"],
                last_at=data["last_at"],
            )
            for event_type, data in summary_dict.items()
        ]

    async def get_all_events(
        self,
        event_type: Optional[EventType] = None,
        session_id: Optional[uuid.UUID] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> EventListResponse:
        """查询所有事件列表（管理员用）"""
        conditions = []
        
        if event_type:
            conditions.append(AnalyticsEvent.event_type == event_type.value)
        if session_id:
            conditions.append(AnalyticsEvent.session_id == session_id)
        if start_time:
            conditions.append(AnalyticsEvent.created_at >= start_time)
        if end_time:
            conditions.append(AnalyticsEvent.created_at <= end_time)

        # 查询总数
        if conditions:
            count_stmt = select(func.count(AnalyticsEvent.id)).where(and_(*conditions))
        else:
            count_stmt = select(func.count(AnalyticsEvent.id))
            
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        # 分页查询
        stmt = select(AnalyticsEvent)
        if conditions:
            stmt = stmt.where(and_(*conditions))
            
        stmt = stmt.order_by(desc(AnalyticsEvent.created_at))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(stmt)
        events = result.scalars().all()

        return EventListResponse(
            events=[
                AnalyticsEventSchema(
                    id=str(e.id),
                    user_id=str(e.user_id),
                    session_id=str(e.session_id) if e.session_id else None,
                    event_type=e.event_type,
                    event_data=e.event_data,
                    created_at=e.created_at,
                    ip_address=e.ip_address,
                    user_agent=e.user_agent,
                )
                for e in events
            ],
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total,
        )

    async def get_event_summary_all(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[EventSummary]:
        """获取所有事件统计摘要（管理员用）"""
        conditions = []
        if start_time:
            conditions.append(AnalyticsEvent.created_at >= start_time)
        if end_time:
            conditions.append(AnalyticsEvent.created_at <= end_time)

        stmt = select(AnalyticsEvent)
        if conditions:
            stmt = stmt.where(and_(*conditions))
            
        result = await self.db.execute(stmt)
        events = result.scalars().all()

        # 按事件类型分组统计
        summary_dict: Dict[str, Dict[str, Any]] = {}
        for event in events:
            if event.event_type not in summary_dict:
                summary_dict[event.event_type] = {
                    "count": 0,
                    "first_at": event.created_at,
                    "last_at": event.created_at,
                }
            summary_dict[event.event_type]["count"] += 1
            if event.created_at < summary_dict[event.event_type]["first_at"]:
                summary_dict[event.event_type]["first_at"] = event.created_at
            if event.created_at > summary_dict[event.event_type]["last_at"]:
                summary_dict[event.event_type]["last_at"] = event.created_at

        return [
            EventSummary(
                event_type=event_type,
                count=data["count"],
                first_at=data["first_at"],
                last_at=data["last_at"],
            )
            for event_type, data in summary_dict.items()
        ]





    # ===== 数据汇出方法（带 PII 遮罩）=====

    async def export_user_data(
        self,
        user_id: uuid.UUID,
        include_events: bool = True,
        include_profile: bool = True,
        apply_pii_mask: bool = True,
    ) -> Dict[str, Any]:
        """
        汇出用户资料（需求 9.7）
        
        安全要求：
        - 应用 PII 遮罩和去识别化
        - 联络方式（电话/邮箱）应被遮罩
        - IP 地址应被遮罩
        
        Args:
            user_id: 用户 ID
            include_events: 是否包含事件数据
            include_profile: 是否包含健康档案
            apply_pii_mask: 是否应用 PII 遮罩（默认 True）
            
        Returns:
            dict: 汇出的用户资料
        """
        from app.core.security import PIIMasker
        from app.services.security_compliance import deidentification_service
        # from app.models.user import User, HealthProfile, Consent
        from app.models.user import User, UserConsent  # 使用新的模型名称
        
        export_data: Dict[str, Any] = {
            "exported_at": datetime.utcnow().isoformat(),
            "user_id": str(user_id),
        }
        
        # 获取用户基本信息
        user_stmt = select(User).where(User.id == user_id)
        user_result = await self.db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if user:
            user_data = {
                "id": str(user.id),
                "contact": user.contact,
                "contact_type": user.contact_type,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            }
            
            # 应用 PII 遮罩
            if apply_pii_mask:
                user_data["contact"] = PIIMasker.mask_contact(
                    user.contact, user.contact_type
                )
            
            export_data["user"] = user_data
        
        # 获取同意记录
        consent_stmt = select(Consent).where(Consent.user_id == user_id)
        consent_result = await self.db.execute(consent_stmt)
        consents = consent_result.scalars().all()
        
        consent_data = []
        for consent in consents:
            c_data = {
                "id": str(consent.id),
                "health_data_consent": consent.health_data_consent,
                "marketing_consent": consent.marketing_consent,
                "version": consent.version,
                "consented_at": consent.consented_at.isoformat() if consent.consented_at else None,
                "ip_address": consent.ip_address,
            }
            
            # 应用 PII 遮罩
            if apply_pii_mask:
                c_data["ip_address"] = PIIMasker.mask_ip(consent.ip_address)
            
            consent_data.append(c_data)
        
        export_data["consents"] = consent_data
        
        # 获取健康档案
        if include_profile:
            profile_stmt = select(HealthProfile).where(HealthProfile.user_id == user_id)
            profile_result = await self.db.execute(profile_stmt)
            profiles = profile_result.scalars().all()
            
            profile_data = []
            for profile in profiles:
                p_data = {
                    "id": str(profile.id),
                    "allergies": profile.allergies,
                    "chronic_conditions": profile.chronic_conditions,
                    "medications": profile.medications,
                    "goals": profile.goals,
                    "dietary_preferences": profile.dietary_preferences,
                    "budget_min": float(profile.budget_min) if profile.budget_min else None,
                    "budget_max": float(profile.budget_max) if profile.budget_max else None,
                    "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
                }
                profile_data.append(p_data)
            
            export_data["health_profiles"] = profile_data
        
        # 获取事件数据
        if include_events:
            events_response = await self.get_events_by_user(
                user_id=user_id,
                page=1,
                page_size=1000,  # 最多汇出 1000 条事件
            )
            
            event_data = []
            for event in events_response.events:
                e_data = {
                    "id": event.id,
                    "event_type": event.event_type,
                    "event_data": event.event_data,
                    "created_at": event.created_at.isoformat() if event.created_at else None,
                    "ip_address": event.ip_address,
                    "user_agent": event.user_agent,
                }
                
                # 应用 PII 遮罩
                if apply_pii_mask and event.ip_address:
                    e_data["ip_address"] = PIIMasker.mask_ip(event.ip_address)
                
                event_data.append(e_data)
            
            export_data["events"] = event_data
            export_data["events_total"] = events_response.total
        
        # 【去识别化处理】使用高级去识别化服务
        if apply_pii_mask:
            # 使用去识别化服务进行更全面的 PII 处理
            export_data = deidentification_service.deidentify_user_data(
                export_data,
                mode="mask"  # 遮罩模式：保留部分信息用于识别
            )
        
        return export_data

    async def export_masked_user_contact(
        self,
        user_id: uuid.UUID,
    ) -> Dict[str, str]:
        """
        获取遮罩后的用户联络方式
        
        Args:
            user_id: 用户 ID
            
        Returns:
            dict: 包含遮罩后的联络方式
        """
        from app.core.security import PIIMasker
        from app.models.user import User
        
        user_stmt = select(User).where(User.id == user_id)
        user_result = await self.db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if not user:
            return {"contact": "", "contact_type": ""}
        
        return {
            "contact": PIIMasker.mask_contact(user.contact, user.contact_type),
            "contact_type": user.contact_type,
        }


def create_analytics_service(db: AsyncSession) -> AnalyticsService:
    """创建分析服务实例"""
    return AnalyticsService(db=db)
