"""商业服务 API 路由"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.commerce import (
    CommerceService,
    CommerceSlotSchema,
    RedirectResult,
    SlotType,
    SyncResult,
    create_commerce_service,
)

router = APIRouter(prefix="/commerce", tags=["commerce"])


class ClickRequest(BaseModel):
    """点击请求"""
    session_id: str
    recommendation_item_id: str
    slot_type: str
    item_id: str


class ProductMappingRequest(BaseModel):
    """商品映射请求"""
    rec_key: str
    slot_type: str
    product_id: Optional[str] = None
    offer_id: Optional[str] = None
    priority: int = 0


class PartnerOfferRequest(BaseModel):
    """合作商 Offer 请求"""
    partner_id: str
    title: str
    redirect_url: str
    payout: float
    description: Optional[str] = None
    image_url: Optional[str] = None
    cap: Optional[int] = None


@router.get("/products/{rec_key}", response_model=Optional[CommerceSlotSchema])
async def get_products_for_recommendation(
    rec_key: str,
    db: AsyncSession = Depends(get_db),
) -> Optional[CommerceSlotSchema]:
    """获取推荐对应的商品卡位"""
    service = create_commerce_service(db)
    return await service.get_products_for_recommendation(rec_key)


@router.get("/out")
async def redirect_with_tracking(
    request: Request,
    user_id: str = Query(...),
    session_id: str = Query(...),
    item_id: str = Query(...),
    slot_type: str = Query(...),
    recommendation_item_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """记录点击并 302 跳转到目标 URL"""
    service = create_commerce_service(db)

    try:
        result = await service.record_click_and_redirect(
            user_id=uuid.UUID(user_id),
            session_id=uuid.UUID(session_id),
            recommendation_item_id=uuid.UUID(recommendation_item_id),
            slot_type=slot_type,
            item_id=item_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        return RedirectResponse(url=result.redirect_url, status_code=302)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process click: {str(e)}")


@router.post("/click", response_model=RedirectResult)
async def record_click(
    request: Request,
    click_request: ClickRequest,
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> RedirectResult:
    """记录点击并返回跳转 URL（API 方式）"""
    service = create_commerce_service(db)

    try:
        return await service.record_click_and_redirect(
            user_id=uuid.UUID(user_id),
            session_id=uuid.UUID(click_request.session_id),
            recommendation_item_id=uuid.UUID(click_request.recommendation_item_id),
            slot_type=click_request.slot_type,
            item_id=click_request.item_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process click: {str(e)}")


@router.post("/sync", response_model=SyncResult)
async def sync_shopify_products(
    db: AsyncSession = Depends(get_db),
) -> SyncResult:
    """同步 Shopify 商品（管理员接口）"""
    service = create_commerce_service(db)
    return await service.sync_shopify_products()


@router.post("/mappings", response_model=dict)
async def create_product_mapping(
    mapping_request: ProductMappingRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """创建商品映射"""
    service = create_commerce_service(db)

    slot_type = SlotType(mapping_request.slot_type)
    product_id = uuid.UUID(mapping_request.product_id) if mapping_request.product_id else None
    offer_id = uuid.UUID(mapping_request.offer_id) if mapping_request.offer_id else None

    mapping = await service.create_product_mapping(
        rec_key=mapping_request.rec_key,
        slot_type=slot_type,
        product_id=product_id,
        offer_id=offer_id,
        priority=mapping_request.priority,
    )

    return {
        "id": str(mapping.id),
        "rec_key": mapping.rec_key,
        "slot_type": mapping.slot_type,
        "priority": mapping.priority,
    }


@router.get("/mappings/{rec_key}")
async def get_mappings(
    rec_key: str,
    db: AsyncSession = Depends(get_db),
) -> list:
    """获取 rec_key 的所有映射"""
    service = create_commerce_service(db)
    mappings = await service.get_mappings_for_rec_key(rec_key)

    return [
        {
            "id": str(m.id),
            "rec_key": m.rec_key,
            "slot_type": m.slot_type,
            "product_id": str(m.product_id) if m.product_id else None,
            "offer_id": str(m.offer_id) if m.offer_id else None,
            "priority": m.priority,
            "active": m.active,
        }
        for m in mappings
    ]


@router.post("/offers", response_model=dict)
async def create_partner_offer(
    offer_request: PartnerOfferRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """创建合作商 Offer"""
    service = create_commerce_service(db)

    from decimal import Decimal
    offer = await service.create_partner_offer(
        partner_id=offer_request.partner_id,
        title=offer_request.title,
        redirect_url=offer_request.redirect_url,
        payout=Decimal(str(offer_request.payout)),
        description=offer_request.description,
        image_url=offer_request.image_url,
        cap=offer_request.cap,
    )

    return {
        "id": str(offer.id),
        "partner_id": offer.partner_id,
        "title": offer.title,
        "sponsored": offer.sponsored,  # 必须为 True
        "active": offer.active,
    }


@router.get("/offers")
async def list_partner_offers(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
) -> list:
    """列出合作商 Offers"""
    service = create_commerce_service(db)
    offers = await service.list_partner_offers(active_only=active_only)

    return [
        {
            "id": str(o.id),
            "partner_id": o.partner_id,
            "title": o.title,
            "description": o.description,
            "payout": float(o.payout),
            "cap": o.cap,
            "current_clicks": o.current_clicks,
            "sponsored": o.sponsored,
            "active": o.active,
        }
        for o in offers
    ]


@router.get("/offers/{offer_id}")
async def get_partner_offer(
    offer_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """获取合作商 Offer"""
    service = create_commerce_service(db)
    offer = await service.get_partner_offer(uuid.UUID(offer_id))

    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    return {
        "id": str(offer.id),
        "partner_id": offer.partner_id,
        "title": offer.title,
        "description": offer.description,
        "image_url": offer.image_url,
        "redirect_url": offer.redirect_url,
        "payout": float(offer.payout),
        "cap": offer.cap,
        "current_clicks": offer.current_clicks,
        "sponsored": offer.sponsored,
        "active": offer.active,
    }


@router.delete("/offers/{offer_id}")
async def deactivate_partner_offer(
    offer_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """停用合作商 Offer"""
    service = create_commerce_service(db)
    success = await service.deactivate_partner_offer(uuid.UUID(offer_id))

    if not success:
        raise HTTPException(status_code=404, detail="Offer not found")

    return {"success": True, "message": "Offer deactivated"}

