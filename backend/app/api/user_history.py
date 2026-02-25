"""用户历史记录和收藏 API"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth_deps import get_current_user
from app.models.user import User
from app.models.user_history import QuizHistory, FavoriteProduct
from app.models.product import Product
from app.services.security_compliance import audit_service, encryption_service
import json
import logging

router = APIRouter(prefix="/api/user", tags=["user_history"])
logger = logging.getLogger(__name__)


# ============================================================================
# Schemas
# ============================================================================

class QuizHistoryResponse(BaseModel):
    """问卷历史记录响应"""
    id: str
    session_id: str
    answers: dict
    health_data: Optional[dict]
    recommendations: dict
    ai_generated: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class FavoriteProductResponse(BaseModel):
    """收藏商品响应"""
    id: str
    product_id: str
    product_name: str
    product_image: Optional[str]
    partner_name: Optional[str]
    price: Optional[float]
    currency: str
    note: Optional[str]
    created_at: datetime


class AddFavoriteRequest(BaseModel):
    """添加收藏请求"""
    product_id: str
    note: Optional[str] = None


# ============================================================================
# 问卷历史记录 API
# ============================================================================

@router.get("/history", response_model=List[QuizHistoryResponse])
async def get_quiz_history(
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户的问卷历史记录
    
    - limit: 返回数量限制（默认 10）
    - offset: 偏移量（默认 0）
    """
    # 【访问审计】记录历史记录访问
    audit_service.log_access(
        user_id=current_user.id,
        resource_type="quiz_history",
        resource_id=str(current_user.id),
        action="list",
        ip_address="unknown",  # 在实际使用中应从 request 获取
        success=True
    )
    
    result = await db.execute(
        select(QuizHistory)
        .where(QuizHistory.user_id == current_user.id)
        .order_by(QuizHistory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    history = result.scalars().all()
    
    # 【静态加密】解密历史记录
    decrypted_history = []
    for h in history:
        try:
            # 检查是否是加密数据（新格式）
            if isinstance(h.answers, dict) and "encrypted" in h.answers:
                # 解密数据
                decrypted_answers = json.loads(
                    encryption_service.decrypt(h.answers["encrypted"])
                )
                decrypted_health_data = None
                if h.health_data and isinstance(h.health_data, dict) and "encrypted" in h.health_data:
                    decrypted_health_data = json.loads(
                        encryption_service.decrypt(h.health_data["encrypted"])
                    )
                decrypted_recommendations = json.loads(
                    encryption_service.decrypt(h.recommendations["encrypted"])
                )
                
                decrypted_history.append(QuizHistoryResponse(
                    id=str(h.id),
                    session_id=h.session_id,
                    answers=decrypted_answers,
                    health_data=decrypted_health_data,
                    recommendations=decrypted_recommendations,
                    ai_generated=h.ai_generated,
                    created_at=h.created_at
                ))
            else:
                # 旧格式（未加密）
                decrypted_history.append(QuizHistoryResponse(
                    id=str(h.id),
                    session_id=h.session_id,
                    answers=h.answers,
                    health_data=h.health_data,
                    recommendations=h.recommendations,
                    ai_generated=h.ai_generated,
                    created_at=h.created_at
                ))
        except Exception as e:
            logger.error(f"Failed to decrypt history {h.id}: {e}")
            # 跳过无法解密的记录
            continue
    
    return decrypted_history


@router.get("/history/{session_id}", response_model=QuizHistoryResponse)
async def get_quiz_history_detail(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取特定问卷历史记录的详情"""
    result = await db.execute(
        select(QuizHistory)
        .where(
            QuizHistory.session_id == session_id,
            QuizHistory.user_id == current_user.id
        )
    )
    history = result.scalar_one_or_none()
    
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="History not found"
        )
    
    # 【静态加密】解密历史记录
    try:
        # 检查是否是加密数据（新格式）
        if isinstance(history.answers, dict) and "encrypted" in history.answers:
            # 解密数据
            decrypted_answers = json.loads(
                encryption_service.decrypt(history.answers["encrypted"])
            )
            decrypted_health_data = None
            if history.health_data and isinstance(history.health_data, dict) and "encrypted" in history.health_data:
                decrypted_health_data = json.loads(
                    encryption_service.decrypt(history.health_data["encrypted"])
                )
            decrypted_recommendations = json.loads(
                encryption_service.decrypt(history.recommendations["encrypted"])
            )
            
            return QuizHistoryResponse(
                id=str(history.id),
                session_id=history.session_id,
                answers=decrypted_answers,
                health_data=decrypted_health_data,
                recommendations=decrypted_recommendations,
                ai_generated=history.ai_generated,
                created_at=history.created_at
            )
        else:
            # 旧格式（未加密）
            return QuizHistoryResponse(
                id=str(history.id),
                session_id=history.session_id,
                answers=history.answers,
                health_data=history.health_data,
                recommendations=history.recommendations,
                ai_generated=history.ai_generated,
                created_at=history.created_at
            )
    except Exception as e:
        logger.error(f"Failed to decrypt history {history.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt history data"
        )


# ============================================================================
# 收藏功能 API
# ============================================================================

@router.get("/favorites", response_model=List[FavoriteProductResponse])
async def get_favorites(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户收藏的商品列表"""
    result = await db.execute(
        select(FavoriteProduct, Product)
        .join(Product, FavoriteProduct.product_id == Product.id)
        .where(FavoriteProduct.user_id == current_user.id)
        .order_by(FavoriteProduct.created_at.desc())
    )
    favorites = result.all()
    
    return [
        FavoriteProductResponse(
            id=str(fav.id),
            product_id=str(fav.product_id),
            product_name=product.name,
            product_image=product.image_url,
            partner_name=product.partner_name,
            price=product.price,
            currency=product.currency,
            note=fav.note,
            created_at=fav.created_at
        )
        for fav, product in favorites
    ]


@router.post("/favorites", status_code=status.HTTP_201_CREATED)
async def add_favorite(
    request: AddFavoriteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """添加商品到收藏"""
    # 检查商品是否存在
    result = await db.execute(
        select(Product).where(Product.id == UUID(request.product_id))
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # 检查是否已收藏
    result = await db.execute(
        select(FavoriteProduct).where(
            FavoriteProduct.user_id == current_user.id,
            FavoriteProduct.product_id == UUID(request.product_id)
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product already in favorites"
        )
    
    # 创建收藏记录
    favorite = FavoriteProduct(
        user_id=current_user.id,
        product_id=UUID(request.product_id),
        note=request.note
    )
    db.add(favorite)
    await db.commit()
    
    return {"message": "Product added to favorites", "id": str(favorite.id)}


@router.delete("/favorites/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """从收藏中移除商品"""
    result = await db.execute(
        delete(FavoriteProduct).where(
            FavoriteProduct.user_id == current_user.id,
            FavoriteProduct.product_id == UUID(product_id)
        )
    )
    
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found"
        )
    
    await db.commit()
    return None


@router.get("/favorites/check/{product_id}")
async def check_favorite(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """检查商品是否已收藏"""
    result = await db.execute(
        select(FavoriteProduct).where(
            FavoriteProduct.user_id == current_user.id,
            FavoriteProduct.product_id == UUID(product_id)
        )
    )
    favorite = result.scalar_one_or_none()
    
    return {"is_favorite": favorite is not None}


# ============================================================================
# 用户数据导出 API (GDPR 合规)
# ============================================================================

@router.get("/export")
async def export_user_data(
    include_sensitive: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    导出用户数据 (GDPR 合规)
    
    - include_sensitive: 是否包含敏感数据（默认 False，去识别化）
    
    返回用户的所有数据，包括问卷历史、收藏、推荐结果等。
    """
    from app.services.security_compliance import deidentification_service
    from app.core.security import PIIMasker
    
    # 【访问审计】记录数据导出
    audit_service.log_access(
        user_id=current_user.id,
        resource_type="user_data_export",
        resource_id=str(current_user.id),
        action="export",
        ip_address="unknown",
        success=True
    )
    
    # 获取用户基本信息
    user_info = {
        "id": str(current_user.id),
        "contact": current_user.contact,
        "contact_type": current_user.contact_type,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }
    
    # 获取问卷历史
    result = await db.execute(
        select(QuizHistory)
        .where(QuizHistory.user_id == current_user.id)
        .order_by(QuizHistory.created_at.desc())
    )
    history = result.scalars().all()
    history_data = []
    for h in history:
        try:
            # 处理加密数据
            if isinstance(h.answers, dict) and "encrypted" in h.answers:
                answers = json.loads(encryption_service.decrypt(h.answers["encrypted"]))
                recommendations = json.loads(encryption_service.decrypt(h.recommendations["encrypted"]))
                health_data = None
                if h.health_data and isinstance(h.health_data, dict) and "encrypted" in h.health_data:
                    health_data = json.loads(encryption_service.decrypt(h.health_data["encrypted"]))
            else:
                answers = h.answers
                recommendations = h.recommendations
                health_data = h.health_data
            
            history_data.append({
                "session_id": h.session_id,
                "answers": answers,
                "health_data": health_data,
                "recommendations": recommendations,
                "created_at": h.created_at.isoformat() if h.created_at else None
            })
        except Exception as e:
            logger.error(f"Failed to decrypt history for export: {e}")
            continue
    
    # 获取收藏列表
    result = await db.execute(
        select(FavoriteProduct, Product)
        .join(Product, FavoriteProduct.product_id == Product.id)
        .where(FavoriteProduct.user_id == current_user.id)
    )
    favorites = result.all()
    favorites_data = [
        {
            "product_id": str(fav.product_id),
            "product_name": product.name,
            "note": fav.note,
            "created_at": fav.created_at.isoformat() if fav.created_at else None
        }
        for fav, product in favorites
    ]
    
    # 组装完整数据
    full_data = {
        "user": user_info,
        "quiz_history": history_data,
        "favorites": favorites_data,
        "exported_at": datetime.utcnow().isoformat()
    }
    
    # 【数据去识别化】
    if not include_sensitive:
        # 遮罩 PII
        full_data["user"]["contact"] = PIIMasker.mask_contact(
            full_data["user"]["contact"],
            full_data["user"]["contact_type"]
        )
        # 使用去识别化服务
        full_data = deidentification_service.deidentify_data(full_data, mode="export")
    
    return {
        "success": True,
        "data": full_data,
        "deidentified": not include_sensitive,
        "message": "用户数据导出成功" if include_sensitive else "用户数据导出成功（已去识别化）"
    }

