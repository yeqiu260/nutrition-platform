"""推荐 API 路由

实现需求：
- 4.1: 当推荐会话创建时，推荐引擎应生成恰好 5 个营养推荐
- 4.8: 对于每个推荐项，推荐引擎应包含商品卡位
- 9.8: 平台应在所有推荐页面显示健康免责声明和专业咨询提示
- 9.5: 平台应通过适当的授权检查防止不安全的直接物件引用（IDOR）攻击
"""

from datetime import datetime
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import IDORProtection, Role, SecurityContext
from app.models.recommendation import RecommendationItem as RecommendationItemModel
from app.models.recommendation import RecommendationSession
from app.models.user import User
from app.services.security_compliance import audit_service
from app.services.recommendation import (
    CommerceSlot,
    HealthProfile as ServiceHealthProfile,
    LocalizedString,
    RecommendationEngine,
    RecommendationItem,
    RecommendationResult,
    SafetyInfo,
    get_disclaimer,
)

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


# ============================================================================
# 请求/响应模型
# ============================================================================

class GenerateRecommendationsRequest(BaseModel):
    """生成推荐请求"""
    session_id: str = Field(..., description="推荐会话 ID")


class RecommendationItemResponse(BaseModel):
    """推荐项响应"""
    rank: int
    rec_key: str
    name: LocalizedString
    why: List[str]
    safety: SafetyInfo
    confidence: int
    commerce_slot: CommerceSlot


class RecommendationResultResponse(BaseModel):
    """推荐结果响应"""
    session_id: str
    generated_at: datetime
    items: List[RecommendationItemResponse]
    disclaimer: str
    requires_review: bool


class RecommendationStatusResponse(BaseModel):
    """推荐状态响应"""
    session_id: str
    status: str  # PENDING | GENERATED | REVIEWED | PUBLISHED
    requires_review: bool
    created_at: datetime
    reviewed_at: Optional[datetime] = None


# ============================================================================
# 服务依赖
# ============================================================================

class RecommendationService:
    """推荐服务 - 封装推荐引擎和数据库操作"""
    
    def __init__(self, db: AsyncSession):
        """初始化推荐服务"""
        self.db = db
        self.engine = RecommendationEngine()
    
    async def get_session(self, session_id: UUID) -> Optional[RecommendationSession]:
        """获取推荐会话"""
        result = await self.db.execute(
            select(RecommendationSession)
            .where(RecommendationSession.id == session_id)
            .options(selectinload(RecommendationSession.items))
        )
        return result.scalar_one_or_none()
    
    async def verify_session_ownership(
        self,
        session_id: UUID,
        user_id: UUID,
        role: Role = Role.USER,
    ) -> RecommendationSession:
        """
        验证推荐会话所有权（IDOR 防护）
        
        Args:
            session_id: 推荐会话 ID
            user_id: 当前用户 ID
            role: 用户角色
            
        Returns:
            RecommendationSession: 推荐会话对象
            
        Raises:
            HTTPException: 如果会话不存在或用户无权访问
        """
        session = await self.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        # IDOR 防护检查
        IDORProtection.check_resource_ownership(user_id, session.user_id, role)
        
        # 【访问审计】记录推荐会话访问
        audit_service.log_access(
            user_id=user_id,
            resource_type="recommendation_session",
            resource_id=str(session_id),
            action="read",
            ip_address="unknown",  # 在实际使用中应从 request 获取
            success=True
        )
        
        return session
    
    # 注释掉旧的 HealthProfile 相关方法（使用新的 quiz API）
    # async def get_health_profile(self, profile_id: UUID) -> Optional[ServiceHealthProfile]:
    #     """获取健康档案"""
    #     # TODO: 实现新的健康档案获取逻辑
    #     pass
    
    # async def _build_service_profile(
    #     self, health_profile: Any
    # ) -> ServiceHealthProfile:
    #     """构建服务层健康档案"""
    #     # TODO: 实现新的健康档案构建逻辑
    #     pass
    
    async def generate_recommendations(
        self, session_id: UUID, user_id: UUID, role: Role = Role.USER
    ) -> RecommendationResult:
        """
        生成推荐（使用混合评分算法）
        
        注意：此方法依赖旧的 HealthProfile 模型，已被新的 quiz 系统替代
        """
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="此 API 已被 /api/quiz/submit 替代，请使用新的问卷系统"
        )
        
        # 旧代码已注释
        # # IDOR 防护：验证会话所有权
        # session = await self.verify_session_ownership(session_id, user_id, role)
        # 
        # # 检查状态
        # if session.status not in ["PENDING", "GENERATED"]:
        #     raise ValueError(f"Session {session_id} is in invalid state: {session.status}")
        # 
        # # 获取健康档案
        # health_profile = await self.get_health_profile(session.health_profile_id)
        # if not health_profile:
        #     raise ValueError(f"Health profile not found for session {session_id}")
        # 
        # # 构建服务层健康档案
        # service_profile = await self._build_service_profile(health_profile)
        # 
        # # 生成推荐
        # result = await self.engine.generate(
        #     session_id=str(session_id),
        #     profile=service_profile,
        #     use_llm=use_llm,
        # )
        # 
        # # 保存推荐项到数据库
        # await self._save_recommendation_items(session, result)
        # 
        # # 更新会话状态
        # session.status = "GENERATED"
        # session.requires_review = result.requires_review
        # await self.db.commit()
        # 
        # return result
    
    async def _save_recommendation_items(
        self, session: RecommendationSession, result: RecommendationResult
    ) -> None:
        """保存推荐项到数据库"""
        # 删除旧的推荐项
        for item in session.items:
            await self.db.delete(item)
        
        # 创建新的推荐项
        for item in result.items:
            db_item = RecommendationItemModel(
                session_id=session.id,
                rank=item.rank,
                rec_key=item.rec_key,
                name={"zh_tw": item.name.zh_tw, "en": item.name.en},
                why_reasons=item.why,
                safety_info={
                    "warnings": item.safety.warnings,
                    "requires_professional_consult": item.safety.requires_professional_consult,
                    "interactions": [
                        {
                            "drug": i.drug,
                            "nutrient": i.nutrient,
                            "severity": i.severity,
                            "description": i.description,
                        }
                        for i in item.safety.interactions
                    ],
                },
                confidence=item.confidence,
                commerce_type=item.commerce_slot.type,
                commerce_id=None,  # 后续由商业服务填充
            )
            self.db.add(db_item)
        
        await self.db.flush()
    
    async def get_recommendations(
        self, session_id: UUID, user_id: UUID, role: Role = Role.USER
    ) -> Optional[RecommendationResult]:
        """
        获取推荐结果
        
        Args:
            session_id: 推荐会话 ID
            user_id: 当前用户 ID（用于 IDOR 检查）
            role: 用户角色
            
        Returns:
            RecommendationResult: 推荐结果，如果不存在则返回 None
            
        Raises:
            HTTPException: 如果用户无权访问该会话
        """
        # IDOR 防护：验证会话所有权
        session = await self.verify_session_ownership(session_id, user_id, role)
        
        if not session.items:
            return None
        
        # 从数据库构建推荐结果
        items = []
        for db_item in sorted(session.items, key=lambda x: x.rank):
            name_dict = db_item.name
            safety_dict = db_item.safety_info
            
            item = RecommendationItem(
                rank=db_item.rank,
                rec_key=db_item.rec_key,
                name=LocalizedString(
                    zh_tw=name_dict.get("zh_tw", db_item.rec_key),
                    en=name_dict.get("en", db_item.rec_key),
                ),
                why=db_item.why_reasons,
                safety=SafetyInfo(
                    warnings=safety_dict.get("warnings", []),
                    requires_professional_consult=safety_dict.get(
                        "requires_professional_consult", False
                    ),
                    interactions=[],
                ),
                confidence=db_item.confidence,
                commerce_slot=CommerceSlot(
                    type=db_item.commerce_type,
                    product_id=str(db_item.commerce_id) if db_item.commerce_id else None,
                ),
            )
            items.append(item)
        
        return RecommendationResult(
            session_id=str(session_id),
            generated_at=session.created_at,
            items=items,
            disclaimer=get_disclaimer(),
            requires_review=session.requires_review,
        )
    
    async def get_session_status(
        self, session_id: UUID, user_id: UUID, role: Role = Role.USER
    ) -> Optional[RecommendationStatusResponse]:
        """
        获取推荐会话状态
        
        Args:
            session_id: 推荐会话 ID
            user_id: 当前用户 ID（用于 IDOR 检查）
            role: 用户角色
            
        Returns:
            RecommendationStatusResponse: 会话状态
            
        Raises:
            HTTPException: 如果用户无权访问该会话
        """
        # IDOR 防护：验证会话所有权
        session = await self.verify_session_ownership(session_id, user_id, role)
        
        return RecommendationStatusResponse(
            session_id=str(session_id),
            status=session.status,
            requires_review=session.requires_review,
            created_at=session.created_at,
            reviewed_at=session.reviewed_at,
        )


async def get_recommendation_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RecommendationService:
    """获取推荐服务依赖"""
    return RecommendationService(db)


async def get_current_user_id(
    authorization: str = Header(None),
) -> UUID:
    """从 Authorization header 中提取并验证用户 ID"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = authorization[7:]

    from app.services.auth import AuthService
    from app.core.database import async_session_maker
    from app.core.redis import get_redis

    async with async_session_maker() as db:
        redis = await get_redis()
        auth_service = AuthService(db, redis)
        user_id = auth_service.verify_jwt_token(token)

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        return UUID(user_id)


async def get_current_user_role(
    authorization: str = Header(None),
) -> Role:
    """从 Authorization header 中提取用户角色"""
    if not authorization or not authorization.startswith("Bearer "):
        return Role.USER

    token = authorization[7:]

    from app.services.auth import AuthService
    from app.core.database import async_session_maker
    from app.core.redis import get_redis

    async with async_session_maker() as db:
        redis = await get_redis()
        auth_service = AuthService(db, redis)
        user_id = auth_service.verify_jwt_token(token)

        if not user_id:
            return Role.USER

        # 获取用户角色
        result = await db.execute(
            select(User).where(User.id == UUID(user_id))
        )
        user = result.scalar_one_or_none()

        if not user:
            return Role.USER

        return Role(user.role) if user.role in [r.value for r in Role] else Role.USER


# ============================================================================
# API 路由
# ============================================================================

@router.post("/generate", response_model=RecommendationResultResponse)
async def generate_recommendations(
    request: GenerateRecommendationsRequest,
    service: Annotated[RecommendationService, Depends(get_recommendation_service)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    role: Annotated[Role, Depends(get_current_user_role)],
) -> RecommendationResultResponse:
    """
    生成推荐（使用混合评分算法）
    
    - **session_id**: 推荐会话 ID（从问卷提交获得）
    
    返回恰好 5 个营养推荐，每个推荐包含：
    - 推荐原因（3-5 条）
    - 安全提示
    - 信心分数（0-100）
    - 商品卡位
    - 免责声明
    
    算法：混合评分（报告分数 × 0.7 + 问卷分数 × 0.3）
    """
    try:
        session_id = UUID(request.session_id)
        result = await service.generate_recommendations(session_id, user_id, role)
        
        return RecommendationResultResponse(
            session_id=result.session_id,
            generated_at=result.generated_at,
            items=[
                RecommendationItemResponse(
                    rank=item.rank,
                    rec_key=item.rec_key,
                    name=item.name,
                    why=item.why,
                    safety=item.safety,
                    confidence=item.confidence,
                    commerce_slot=item.commerce_slot,
                )
                for item in result.items
            ],
            disclaimer=result.disclaimer,
            requires_review=result.requires_review,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}",
        )


@router.get("/{session_id}", response_model=RecommendationResultResponse)
async def get_recommendations(
    session_id: str,
    service: Annotated[RecommendationService, Depends(get_recommendation_service)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    role: Annotated[Role, Depends(get_current_user_role)],
) -> RecommendationResultResponse:
    """
    获取推荐结果
    
    - **session_id**: 推荐会话 ID
    
    返回已生成的推荐结果，包含免责声明。
    IDOR 防护：用户只能访问自己的推荐会话。
    """
    try:
        session_uuid = UUID(session_id)
        result = await service.get_recommendations(session_uuid, user_id, role)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recommendations not found for session {session_id}",
            )
        
        return RecommendationResultResponse(
            session_id=result.session_id,
            generated_at=result.generated_at,
            items=[
                RecommendationItemResponse(
                    rank=item.rank,
                    rec_key=item.rec_key,
                    name=item.name,
                    why=item.why,
                    safety=item.safety,
                    confidence=item.confidence,
                    commerce_slot=item.commerce_slot,
                )
                for item in result.items
            ],
            disclaimer=result.disclaimer,
            requires_review=result.requires_review,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )


@router.get("/{session_id}/status", response_model=RecommendationStatusResponse)
async def get_recommendation_status(
    session_id: str,
    service: Annotated[RecommendationService, Depends(get_recommendation_service)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    role: Annotated[Role, Depends(get_current_user_role)],
) -> RecommendationStatusResponse:
    """
    获取推荐会话状态
    
    - **session_id**: 推荐会话 ID
    
    返回会话状态：PENDING | GENERATED | REVIEWED | PUBLISHED
    IDOR 防护：用户只能访问自己的推荐会话。
    """
    try:
        session_uuid = UUID(session_id)
        result = await service.get_session_status(session_uuid, user_id, role)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )
        
        return result
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )


@router.get("/disclaimer/{locale}")
async def get_disclaimer_text(locale: str = "zh-TW") -> dict:
    """
    获取免责声明文本
    
    - **locale**: 语言代码（"zh-TW" 或 "en"）
    
    返回对应语言的免责声明文本。
    """
    return {"disclaimer": get_disclaimer(locale)}
