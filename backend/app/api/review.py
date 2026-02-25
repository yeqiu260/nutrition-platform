"""审核队列 API 路由

实现需求 8：审核队列
- 8.1 高风险案例标记
- 8.2 案例详情查询
- 8.3 批准案例
- 8.4 拒绝案例
- 8.5 筛选和分页
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.review import (
    ReviewService,
    ReviewStatus,
    RiskLevel,
    ReviewFilterParams,
    ReviewListResponse,
    ReviewQueueItemSchema,
    ReviewNotFoundError,
    InvalidReviewActionError,
    create_review_service,
)

router = APIRouter(prefix="/review", tags=["review"])


class ApproveRequest(BaseModel):
    """批准请求"""
    resolution_note: Optional[str] = None


class RejectRequest(BaseModel):
    """拒绝请求"""
    resolution_note: str


class AssignRequest(BaseModel):
    """分配审核员请求"""
    reviewer_id: str


class ReviewStatsResponse(BaseModel):
    """审核统计响应"""
    by_status: dict
    pending_by_risk: dict
    total_pending: int


def get_review_service(db: AsyncSession = Depends(get_db)) -> ReviewService:
    """获取审核服务依赖"""
    return create_review_service(db)


@router.get("/list", response_model=ReviewListResponse)
async def get_review_list(
    status: Optional[str] = Query(None, description="筛选状态"),
    risk_level: Optional[str] = Query(None, description="筛选风险等级"),
    assigned_to: Optional[str] = Query(None, description="筛选分配的审核员"),
    date_from: Optional[datetime] = Query(None, description="开始日期"),
    date_to: Optional[datetime] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    include_detail: bool = Query(False, description="是否包含案例详情"),
    service: ReviewService = Depends(get_review_service),
):
    """获取审核列表
    
    需求 8.5：支援按风险等级、状态和日期筛选
    """
    filters = ReviewFilterParams(
        status=ReviewStatus(status) if status else None,
        risk_level=RiskLevel(risk_level) if risk_level else None,
        assigned_to=assigned_to,
        date_from=date_from,
        date_to=date_to,
    )
    
    return await service.get_review_list(
        filters=filters,
        page=page,
        page_size=page_size,
        include_detail=include_detail,
    )


@router.get("/stats", response_model=ReviewStatsResponse)
async def get_review_stats(
    service: ReviewService = Depends(get_review_service),
):
    """获取审核统计信息"""
    stats = await service.get_stats()
    return ReviewStatsResponse(**stats)


@router.get("/{review_id}", response_model=ReviewQueueItemSchema)
async def get_review_detail(
    review_id: str,
    service: ReviewService = Depends(get_review_service),
):
    """获取审核详情
    
    需求 8.2：显示案例详情，包括问卷答案、化验指标和生成的推荐
    """
    try:
        review_uuid = uuid.UUID(review_id)
        return await service.get_review_detail(review_uuid)
    except ReviewNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review {review_id} not found",
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid review ID format",
        )


@router.post("/{review_id}/approve", response_model=ReviewQueueItemSchema)
async def approve_review(
    review_id: str,
    request: ApproveRequest,
    reviewer_id: str = Query(..., description="审核员 ID"),
    service: ReviewService = Depends(get_review_service),
):
    """批准审核
    
    需求 8.3：当审核员批准案例时，向用户发布推荐
    """
    try:
        review_uuid = uuid.UUID(review_id)
        reviewer_uuid = uuid.UUID(reviewer_id)
        
        review = await service.approve_review(
            review_id=review_uuid,
            reviewer_id=reviewer_uuid,
            resolution_note=request.resolution_note,
        )
        
        return await service.get_review_detail(review_uuid)
    except ReviewNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review {review_id} not found",
        )
    except InvalidReviewActionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{review_id}/reject", response_model=ReviewQueueItemSchema)
async def reject_review(
    review_id: str,
    request: RejectRequest,
    reviewer_id: str = Query(..., description="审核员 ID"),
    service: ReviewService = Depends(get_review_service),
):
    """拒绝审核
    
    需求 8.4：当审核员拒绝案例时，通知用户并请求补充资料
    """
    try:
        review_uuid = uuid.UUID(review_id)
        reviewer_uuid = uuid.UUID(reviewer_id)
        
        review = await service.reject_review(
            review_id=review_uuid,
            reviewer_id=reviewer_uuid,
            resolution_note=request.resolution_note,
        )
        
        return await service.get_review_detail(review_uuid)
    except ReviewNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review {review_id} not found",
        )
    except InvalidReviewActionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{review_id}/assign", response_model=ReviewQueueItemSchema)
async def assign_reviewer(
    review_id: str,
    request: AssignRequest,
    service: ReviewService = Depends(get_review_service),
):
    """分配审核员"""
    try:
        review_uuid = uuid.UUID(review_id)
        reviewer_uuid = uuid.UUID(request.reviewer_id)
        
        review = await service.assign_reviewer(
            review_id=review_uuid,
            reviewer_id=reviewer_uuid,
        )
        
        return await service.get_review_detail(review_uuid)
    except ReviewNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review {review_id} not found",
        )
    except InvalidReviewActionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{review_id}/unassign", response_model=ReviewQueueItemSchema)
async def unassign_reviewer(
    review_id: str,
    service: ReviewService = Depends(get_review_service),
):
    """取消分配审核员"""
    try:
        review_uuid = uuid.UUID(review_id)
        
        review = await service.unassign_reviewer(review_id=review_uuid)
        
        return await service.get_review_detail(review_uuid)
    except ReviewNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review {review_id} not found",
        )
    except InvalidReviewActionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
