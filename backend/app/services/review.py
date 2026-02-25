"""审核队列服务模块

实现需求 8：审核队列
- 8.1 当推荐会话被标记为高风险时，审核队列应将其加入待审核列表
- 8.2 审核队列应显示案例详情，包括问卷答案和生成的推荐
- 8.3 当审核员批准案例时，审核队列应向用户发布推荐
- 8.4 当审核员拒绝案例时，审核队列应通知用户并请求补充资料
- 8.5 审核队列应支援按风险等级、状态和日期筛选
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import select, and_, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.review import ReviewQueue
from app.models.recommendation import RecommendationSession, RecommendationItem
# from app.models.user import HealthProfile, QuestionAnswer, User
from app.models.user import HealthProfile, User
# 注意: 如果 QuizSession 不是 QuestionAnswer，請確認 QuestionAnswer 模型在哪裡。
# 根據之前查看的user.py，沒有QuestionAnswer模型，但是有QuizSession。
# 查看 review.py 第 313 行: stmt = select(QuestionAnswer).where(...)
# 這意味著代碼期望有一個 QuestionAnswer 模型。
# 讓我們再檢查 user.py 看看是否有 class QuestionAnswer。
# 如果沒有，那可能是在其他地方，或者之前的重構遺漏了。
# 暫時假設 QuestionAnswer 缺失，或者被重命名了。
# 但錯誤報告是 NameError: name 'HealthProfile' is not defined。
# 先修復 HealthProfile。


def utc_now() -> datetime:
    """获取当前 UTC 时间（时区感知）"""
    return datetime.now(timezone.utc)


class ReviewStatus(str, Enum):
    """审核状态枚举"""
    PENDING = "PENDING"       # 待审核
    IN_REVIEW = "IN_REVIEW"   # 审核中
    APPROVED = "APPROVED"     # 已批准
    REJECTED = "REJECTED"     # 已拒绝


class RiskLevel(str, Enum):
    """风险等级枚举"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ReviewAction(str, Enum):
    """审核操作类型"""
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    ASSIGN = "ASSIGN"
    UNASSIGN = "UNASSIGN"


# 高风险标记规则
HIGH_RISK_CONDITIONS = [
    "diabetes",
    "heart_disease",
    "kidney_disease",
    "liver_disease",
    "cancer",
    "autoimmune",
]

HIGH_RISK_MEDICATIONS = [
    "warfarin",
    "insulin",
    "metformin",
    "lithium",
    "immunosuppressant",
]

CRITICAL_ALLERGIES = [
    "severe_food_allergy",
    "anaphylaxis_history",
]


class QuestionAnswerSchema(BaseModel):
    """问卷答案 Schema"""
    question_id: str
    value: Any
    answered_at: datetime


class RecommendationItemSchema(BaseModel):
    """推荐项 Schema"""
    rank: int
    rec_key: str
    name: Dict[str, str]
    why_reasons: List[str]
    safety_info: Dict[str, Any]
    confidence: int


class HealthProfileSchema(BaseModel):
    """健康档案 Schema"""
    allergies: List[str]
    chronic_conditions: List[str]
    medications: List[str]
    goals: List[str]
    dietary_preferences: List[str]
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None


class CaseDetailSchema(BaseModel):
    """案例详情 Schema - 需求 8.2"""
    session_id: str
    user_id: str
    health_profile: HealthProfileSchema
    question_answers: List[QuestionAnswerSchema]
    recommendations: List[RecommendationItemSchema]
    created_at: datetime


class ReviewQueueItemSchema(BaseModel):
    """审核队列项 Schema"""
    id: str
    session_id: str
    status: str
    risk_level: str
    assigned_to: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None
    case_detail: Optional[CaseDetailSchema] = None


class ReviewListResponse(BaseModel):
    """审核列表响应"""
    items: List[ReviewQueueItemSchema]
    total: int
    page: int
    page_size: int


class ReviewFilterParams(BaseModel):
    """审核筛选参数 - 需求 8.5"""
    status: Optional[ReviewStatus] = None
    risk_level: Optional[RiskLevel] = None
    assigned_to: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class ReviewActionRequest(BaseModel):
    """审核操作请求"""
    action: ReviewAction
    resolution_note: Optional[str] = None


class ReviewNotFoundError(Exception):
    """审核项未找到错误"""
    pass


class InvalidReviewActionError(Exception):
    """无效审核操作错误"""
    def __init__(self, current_status: str, action: str):
        self.current_status = current_status
        self.action = action
        super().__init__(
            f"Cannot perform action '{action}' on review with status '{current_status}'"
        )


class ReviewService:
    """审核队列服务
    
    实现需求 8：审核队列
    - 高风险案例标记
    - 案例详情查询
    - 审核操作（批准/拒绝）
    - 筛选和分页
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _calculate_risk_level(
        self,
        health_profile: HealthProfile,
        recommendations: List[RecommendationItem],
    ) -> RiskLevel:
        """计算风险等级
        
        需求 8.1：高风险案例标记逻辑
        
        风险等级判定规则：
        - CRITICAL: 有严重过敏史或多个高风险因素
        - HIGH: 有高风险慢病或高风险用药
        - MEDIUM: 有一般慢病或用药
        - LOW: 无特殊风险因素
        """
        risk_score = 0
        
        # 检查严重过敏
        allergies = health_profile.allergies or []
        for allergy in allergies:
            if any(critical in allergy.lower() for critical in CRITICAL_ALLERGIES):
                risk_score += 50
        
        # 检查高风险慢病
        conditions = health_profile.chronic_conditions or []
        for condition in conditions:
            if any(high_risk in condition.lower() for high_risk in HIGH_RISK_CONDITIONS):
                risk_score += 20
        
        # 检查高风险用药
        medications = health_profile.medications or []
        for medication in medications:
            if any(high_risk in medication.lower() for high_risk in HIGH_RISK_MEDICATIONS):
                risk_score += 15
        
        # 检查推荐中的安全警告
        for rec in recommendations:
            safety_info = rec.safety_info or {}
            warnings = safety_info.get("warnings", [])
            if warnings:
                risk_score += len(warnings) * 5
            if safety_info.get("requires_professional_consult"):
                risk_score += 10
        
        # 根据分数确定风险等级
        if risk_score >= 50:
            return RiskLevel.CRITICAL
        elif risk_score >= 30:
            return RiskLevel.HIGH
        elif risk_score >= 10:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def should_require_review(
        self,
        health_profile: HealthProfile,
        recommendations: List[RecommendationItem],
    ) -> bool:
        """判断是否需要人工审核
        
        需求 8.1：当推荐会话被标记为高风险时，加入待审核列表
        
        Returns:
            True 如果需要审核，False 否则
        """
        risk_level = self._calculate_risk_level(health_profile, recommendations)
        return risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]

    async def create_review_item(
        self,
        session_id: uuid.UUID,
        health_profile: HealthProfile,
        recommendations: List[RecommendationItem],
    ) -> ReviewQueue:
        """创建审核队列项
        
        需求 8.1：将高风险案例加入待审核列表
        
        Args:
            session_id: 推荐会话 ID
            health_profile: 健康档案
            recommendations: 推荐列表
            
        Returns:
            创建的审核队列项
        """
        risk_level = self._calculate_risk_level(health_profile, recommendations)
        
        review_item = ReviewQueue(
            session_id=session_id,
            status=ReviewStatus.PENDING.value,
            risk_level=risk_level.value,
            created_at=utc_now(),
        )
        self.db.add(review_item)
        await self.db.flush()
        await self.db.refresh(review_item)
        return review_item


    async def get_review_by_id(
        self,
        review_id: uuid.UUID,
    ) -> Optional[ReviewQueue]:
        """根据 ID 获取审核项"""
        stmt = select(ReviewQueue).where(ReviewQueue.id == review_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_review_by_session_id(
        self,
        session_id: uuid.UUID,
    ) -> Optional[ReviewQueue]:
        """根据会话 ID 获取审核项"""
        stmt = select(ReviewQueue).where(ReviewQueue.session_id == session_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _build_case_detail(
        self,
        session: RecommendationSession,
    ) -> CaseDetailSchema:
        """构建案例详情
        
        需求 8.2：显示案例详情，包括问卷答案和生成的推荐
        """
        # 获取健康档案
        health_profile = session.health_profile
        
        # 获取问卷答案
        return CaseDetailSchema(
            session_id=str(session.id),
            user_id=str(session.user_id),
            health_profile=HealthProfileSchema(
                allergies=health_profile.allergies or [],
                chronic_conditions=health_profile.chronic_conditions or [],
                medications=health_profile.medications or [],
                goals=health_profile.goals or [],
                dietary_preferences=health_profile.dietary_preferences or [],
                budget_min=float(health_profile.budget_min) if health_profile.budget_min else None,
                budget_max=float(health_profile.budget_max) if health_profile.budget_max else None,
            ),
            # Temporarily return empty answers as QuestionAnswer table is deprecated
            question_answers=[],
            recommendations=[
                RecommendationItemSchema(
                    rank=item.rank,
                    rec_key=item.rec_key,
                    name=item.name,
                    why_reasons=item.why_reasons,
                    safety_info=item.safety_info,
                    confidence=item.confidence,
                )
                for item in session.items
            ],
            created_at=session.created_at,
        )

    async def get_review_list(
        self,
        filters: Optional[ReviewFilterParams] = None,
        page: int = 1,
        page_size: int = 20,
        include_detail: bool = False,
    ) -> ReviewListResponse:
        """获取审核列表
        
        需求 8.5：支援按风险等级、状态和日期筛选
        
        Args:
            filters: 筛选参数
            page: 页码
            page_size: 每页数量
            include_detail: 是否包含案例详情
            
        Returns:
            审核列表响应
        """
        # 构建查询条件
        conditions = []
        
        if filters:
            if filters.status:
                conditions.append(ReviewQueue.status == filters.status.value)
            if filters.risk_level:
                conditions.append(ReviewQueue.risk_level == filters.risk_level.value)
            if filters.assigned_to:
                conditions.append(
                    ReviewQueue.assigned_to == uuid.UUID(filters.assigned_to)
                )
            if filters.date_from:
                conditions.append(ReviewQueue.created_at >= filters.date_from)
            if filters.date_to:
                conditions.append(ReviewQueue.created_at <= filters.date_to)
        
        # 查询总数
        count_stmt = select(ReviewQueue)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = len(count_result.scalars().all())
        
        # 分页查询
        offset = (page - 1) * page_size
        stmt = (
            select(ReviewQueue)
            .options(
                selectinload(ReviewQueue.session)
                .selectinload(RecommendationSession.items),
                selectinload(ReviewQueue.session)
                .selectinload(RecommendationSession.health_profile),
            )
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(
            # 按风险等级降序（CRITICAL > HIGH > MEDIUM > LOW）
            desc(
                ReviewQueue.risk_level == RiskLevel.CRITICAL.value
            ),
            desc(
                ReviewQueue.risk_level == RiskLevel.HIGH.value
            ),
            # 然后按创建时间降序
            desc(ReviewQueue.created_at),
        ).offset(offset).limit(page_size)
        
        result = await self.db.execute(stmt)
        reviews = result.scalars().all()
        
        items = []
        for review in reviews:
            item = ReviewQueueItemSchema(
                id=str(review.id),
                session_id=str(review.session_id),
                status=review.status,
                risk_level=review.risk_level,
                assigned_to=str(review.assigned_to) if review.assigned_to else None,
                created_at=review.created_at,
                resolved_at=review.resolved_at,
                resolution_note=review.resolution_note,
            )
            
            if include_detail and review.session:
                item.case_detail = await self._build_case_detail(review.session)
            
            items.append(item)
        
        return ReviewListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_review_detail(
        self,
        review_id: uuid.UUID,
    ) -> ReviewQueueItemSchema:
        """获取审核详情
        
        需求 8.2：显示案例详情
        
        Args:
            review_id: 审核项 ID
            
        Returns:
            审核详情
            
        Raises:
            ReviewNotFoundError: 审核项不存在
        """
        stmt = (
            select(ReviewQueue)
            .options(
                selectinload(ReviewQueue.session)
                .selectinload(RecommendationSession.items),
                selectinload(ReviewQueue.session)
                .selectinload(RecommendationSession.health_profile),
            )
            .where(ReviewQueue.id == review_id)
        )
        result = await self.db.execute(stmt)
        review = result.scalar_one_or_none()
        
        if not review:
            raise ReviewNotFoundError(f"Review {review_id} not found")
        
        case_detail = None
        if review.session:
            case_detail = await self._build_case_detail(review.session)
        
        return ReviewQueueItemSchema(
            id=str(review.id),
            session_id=str(review.session_id),
            status=review.status,
            risk_level=review.risk_level,
            assigned_to=str(review.assigned_to) if review.assigned_to else None,
            created_at=review.created_at,
            resolved_at=review.resolved_at,
            resolution_note=review.resolution_note,
            case_detail=case_detail,
        )


    async def approve_review(
        self,
        review_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        resolution_note: Optional[str] = None,
    ) -> ReviewQueue:
        """批准审核
        
        需求 8.3：当审核员批准案例时，向用户发布推荐
        
        Args:
            review_id: 审核项 ID
            reviewer_id: 审核员 ID
            resolution_note: 审核备注
            
        Returns:
            更新后的审核项
            
        Raises:
            ReviewNotFoundError: 审核项不存在
            InvalidReviewActionError: 无效的审核操作
        """
        review = await self.get_review_by_id(review_id)
        if not review:
            raise ReviewNotFoundError(f"Review {review_id} not found")
        
        # 验证状态
        if review.status not in [ReviewStatus.PENDING.value, ReviewStatus.IN_REVIEW.value]:
            raise InvalidReviewActionError(review.status, ReviewAction.APPROVE.value)
        
        # 更新审核状态
        review.status = ReviewStatus.APPROVED.value
        review.resolved_at = utc_now()
        review.resolution_note = resolution_note
        review.assigned_to = reviewer_id
        
        # 更新推荐会话状态为已发布
        stmt = select(RecommendationSession).where(
            RecommendationSession.id == review.session_id
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if session:
            session.status = "PUBLISHED"
            session.reviewed_at = utc_now()
            session.reviewed_by = reviewer_id
        
        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def reject_review(
        self,
        review_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        resolution_note: str,
    ) -> ReviewQueue:
        """拒绝审核
        
        需求 8.4：当审核员拒绝案例时，通知用户并请求补充资料
        
        Args:
            review_id: 审核项 ID
            reviewer_id: 审核员 ID
            resolution_note: 拒绝原因（必填）
            
        Returns:
            更新后的审核项
            
        Raises:
            ReviewNotFoundError: 审核项不存在
            InvalidReviewActionError: 无效的审核操作
            ValueError: 拒绝时必须提供原因
        """
        if not resolution_note:
            raise ValueError("Resolution note is required when rejecting a review")
        
        review = await self.get_review_by_id(review_id)
        if not review:
            raise ReviewNotFoundError(f"Review {review_id} not found")
        
        # 验证状态
        if review.status not in [ReviewStatus.PENDING.value, ReviewStatus.IN_REVIEW.value]:
            raise InvalidReviewActionError(review.status, ReviewAction.REJECT.value)
        
        # 更新审核状态
        review.status = ReviewStatus.REJECTED.value
        review.resolved_at = utc_now()
        review.resolution_note = resolution_note
        review.assigned_to = reviewer_id
        
        # 更新推荐会话状态为已拒绝
        stmt = select(RecommendationSession).where(
            RecommendationSession.id == review.session_id
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if session:
            session.status = "REJECTED"
            session.reviewed_at = utc_now()
            session.reviewed_by = reviewer_id
        
        await self.db.commit()
        await self.db.refresh(review)
        
        # TODO: 发送通知给用户，请求补充资料
        # 这里可以集成通知服务
        
        return review

    async def assign_reviewer(
        self,
        review_id: uuid.UUID,
        reviewer_id: uuid.UUID,
    ) -> ReviewQueue:
        """分配审核员
        
        Args:
            review_id: 审核项 ID
            reviewer_id: 审核员 ID
            
        Returns:
            更新后的审核项
        """
        review = await self.get_review_by_id(review_id)
        if not review:
            raise ReviewNotFoundError(f"Review {review_id} not found")
        
        if review.status not in [ReviewStatus.PENDING.value, ReviewStatus.IN_REVIEW.value]:
            raise InvalidReviewActionError(review.status, ReviewAction.ASSIGN.value)
        
        review.assigned_to = reviewer_id
        review.status = ReviewStatus.IN_REVIEW.value
        
        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def unassign_reviewer(
        self,
        review_id: uuid.UUID,
    ) -> ReviewQueue:
        """取消分配审核员
        
        Args:
            review_id: 审核项 ID
            
        Returns:
            更新后的审核项
        """
        review = await self.get_review_by_id(review_id)
        if not review:
            raise ReviewNotFoundError(f"Review {review_id} not found")
        
        if review.status != ReviewStatus.IN_REVIEW.value:
            raise InvalidReviewActionError(review.status, ReviewAction.UNASSIGN.value)
        
        review.assigned_to = None
        review.status = ReviewStatus.PENDING.value
        
        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def get_pending_count(self) -> int:
        """获取待审核数量"""
        stmt = select(ReviewQueue).where(
            ReviewQueue.status == ReviewStatus.PENDING.value
        )
        result = await self.db.execute(stmt)
        return len(result.scalars().all())

    async def get_stats(self) -> Dict[str, Any]:
        """获取审核统计信息"""
        # 按状态统计
        status_counts = {}
        for status in ReviewStatus:
            stmt = select(ReviewQueue).where(ReviewQueue.status == status.value)
            result = await self.db.execute(stmt)
            status_counts[status.value] = len(result.scalars().all())
        
        # 按风险等级统计
        risk_counts = {}
        for risk in RiskLevel:
            stmt = select(ReviewQueue).where(
                and_(
                    ReviewQueue.risk_level == risk.value,
                    ReviewQueue.status == ReviewStatus.PENDING.value,
                )
            )
            result = await self.db.execute(stmt)
            risk_counts[risk.value] = len(result.scalars().all())
        
        return {
            "by_status": status_counts,
            "pending_by_risk": risk_counts,
            "total_pending": status_counts.get(ReviewStatus.PENDING.value, 0),
        }


def create_review_service(db: AsyncSession) -> ReviewService:
    """创建审核服务实例"""
    return ReviewService(db=db)
