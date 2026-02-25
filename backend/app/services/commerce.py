"""商业服务模块：Shopify 商品同步、商品映射、合作商 Offer、点击追踪"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.analytics import AnalyticsEvent
from app.models.commerce import CommerceClick, PartnerOffer, ShopifyProduct, ProductMapping


class SlotType(str, Enum):
    """商品卡位类型"""
    SHOPIFY = "shopify"
    PARTNER = "partner"


class ShopifyProductSchema(BaseModel):
    """Shopify 商品 Schema"""
    id: str
    variant_id: str
    title: str
    price: Decimal
    currency: str = "TWD"
    image_url: Optional[str] = None
    in_stock: bool = True
    checkout_url: str = ""


class PartnerOfferSchema(BaseModel):
    """合作商 Offer Schema"""
    id: str
    partner_id: str
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    payout: Decimal
    cap: Optional[int] = None
    current_clicks: int = 0
    sponsored: bool = True  # 必须为 True


class CommerceSlotSchema(BaseModel):
    """商品卡位 Schema"""
    type: SlotType
    product: Optional[ShopifyProductSchema] = None
    offer: Optional[PartnerOfferSchema] = None


class SyncResult(BaseModel):
    """同步结果"""
    synced_count: int = 0
    failed_count: int = 0
    errors: List[str] = Field(default_factory=list)


class RedirectResult(BaseModel):
    """跳转结果"""
    redirect_url: str


class ClickEventData(BaseModel):
    """点击事件数据"""
    slot_type: str
    commerce_id: str
    recommendation_item_id: str
    redirect_url: Optional[str] = None



class ShopifyClient:
    """Shopify Admin API 客户端"""

    def __init__(
        self,
        shop_domain: str,
        access_token: str,
        api_version: str = "2024-01",
    ):
        self.shop_domain = shop_domain
        self.access_token = access_token
        self.api_version = api_version
        self.base_url = f"https://{shop_domain}/admin/api/{api_version}"

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """发送 API 请求"""
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def get_products(
        self,
        limit: int = 250,
        since_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取商品列表"""
        params = f"limit={limit}"
        if since_id:
            params += f"&since_id={since_id}"

        result = await self._request("GET", f"products.json?{params}")
        return result.get("products", [])

    async def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """获取单个商品"""
        try:
            result = await self._request("GET", f"products/{product_id}.json")
            return result.get("product")
        except httpx.HTTPStatusError:
            return None

    async def get_inventory_levels(
        self,
        inventory_item_ids: List[str],
    ) -> List[Dict[str, Any]]:
        """获取库存水平"""
        ids = ",".join(inventory_item_ids)
        result = await self._request(
            "GET",
            f"inventory_levels.json?inventory_item_ids={ids}",
        )
        return result.get("inventory_levels", [])


def create_shopify_client() -> Optional[ShopifyClient]:
    """创建 Shopify 客户端"""
    settings = get_settings()
    if not settings.shopify_shop_domain or not settings.shopify_access_token:
        return None
    return ShopifyClient(
        shop_domain=settings.shopify_shop_domain,
        access_token=settings.shopify_access_token,
        api_version=settings.shopify_api_version,
    )


class CommerceService:
    """商业服务"""

    def __init__(
        self,
        db: AsyncSession,
        shopify_client: Optional[ShopifyClient] = None,
    ):
        self.db = db
        self.shopify_client = shopify_client or create_shopify_client()

    async def sync_shopify_products(self) -> SyncResult:
        """同步 Shopify 商品到本地数据库"""
        result = SyncResult()

        if not self.shopify_client:
            result.errors.append("Shopify client not configured")
            return result

        try:
            # 获取所有商品
            products = await self.shopify_client.get_products()

            for product_data in products:
                try:
                    await self._sync_single_product(product_data)
                    result.synced_count += 1
                except Exception as e:
                    result.failed_count += 1
                    result.errors.append(
                        f"Failed to sync product {product_data.get('id')}: {str(e)}"
                    )

        except Exception as e:
            result.errors.append(f"Failed to fetch products: {str(e)}")

        return result

    async def _sync_single_product(self, product_data: Dict[str, Any]) -> None:
        """同步单个商品"""
        shopify_id = str(product_data["id"])

        # 获取第一个变体
        variants = product_data.get("variants", [])
        if not variants:
            return

        variant = variants[0]
        variant_id = str(variant["id"])

        # 获取图片
        images = product_data.get("images", [])
        image_url = images[0]["src"] if images else None

        # 检查库存
        inventory_quantity = variant.get("inventory_quantity", 0)
        in_stock = inventory_quantity > 0

        # 查找或创建商品
        stmt = select(ShopifyProduct).where(ShopifyProduct.shopify_id == shopify_id)
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # 更新现有商品
            existing.shopify_variant_id = variant_id
            existing.title = product_data["title"]
            existing.price = Decimal(str(variant["price"]))
            existing.image_url = image_url
            existing.in_stock = in_stock
            existing.synced_at = datetime.utcnow()
        else:
            # 创建新商品
            new_product = ShopifyProduct(
                shopify_id=shopify_id,
                shopify_variant_id=variant_id,
                title=product_data["title"],
                price=Decimal(str(variant["price"])),
                currency="TWD",
                image_url=image_url,
                in_stock=in_stock,
                synced_at=datetime.utcnow(),
            )
            self.db.add(new_product)

        await self.db.commit()

    async def update_inventory_status(self, shopify_id: str, in_stock: bool) -> bool:
        """更新商品库存状态"""
        stmt = (
            update(ShopifyProduct)
            .where(ShopifyProduct.shopify_id == shopify_id)
            .values(in_stock=in_stock, synced_at=datetime.utcnow())
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def get_product_by_shopify_id(
        self,
        shopify_id: str,
    ) -> Optional[ShopifyProduct]:
        """根据 Shopify ID 获取商品"""
        stmt = select(ShopifyProduct).where(ShopifyProduct.shopify_id == shopify_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()


    async def get_products_for_recommendation(
        self,
        rec_key: str,
    ) -> Optional[CommerceSlotSchema]:
        """获取推荐对应的商品卡位"""
        # 查询映射，按优先级排序
        stmt = (
            select(ProductMapping)
            .where(ProductMapping.rec_key == rec_key)
            .where(ProductMapping.active == True)
            .order_by(ProductMapping.priority.desc())
        )
        result = await self.db.execute(stmt)
        mappings = result.scalars().all()

        if not mappings:
            return None

        # 遍历映射，找到第一个有效的
        for mapping in mappings:
            if mapping.slot_type == SlotType.SHOPIFY and mapping.product_id:
                product = await self._get_product(mapping.product_id)
                if product and product.in_stock:
                    return CommerceSlotSchema(
                        type=SlotType.SHOPIFY,
                        product=ShopifyProductSchema(
                            id=product.shopify_id,
                            variant_id=product.shopify_variant_id,
                            title=product.title,
                            price=product.price,
                            currency=product.currency,
                            image_url=product.image_url,
                            in_stock=product.in_stock,
                            checkout_url=self._build_checkout_url(product),
                        ),
                    )
            elif mapping.slot_type == SlotType.PARTNER and mapping.offer_id:
                offer = await self._get_offer(mapping.offer_id)
                if offer and offer.active:
                    # 检查是否达到点击上限
                    if offer.cap and offer.current_clicks >= offer.cap:
                        continue
                    return CommerceSlotSchema(
                        type=SlotType.PARTNER,
                        offer=PartnerOfferSchema(
                            id=str(offer.id),
                            partner_id=offer.partner_id,
                            title=offer.title,
                            description=offer.description,
                            image_url=offer.image_url,
                            payout=offer.payout,
                            cap=offer.cap,
                            current_clicks=offer.current_clicks,
                            sponsored=True,  # 必须为 True
                        ),
                    )

        return None

    async def _get_product(self, product_id: uuid.UUID) -> Optional[ShopifyProduct]:
        """获取商品"""
        stmt = select(ShopifyProduct).where(ShopifyProduct.id == product_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_offer(self, offer_id: uuid.UUID) -> Optional[PartnerOffer]:
        """获取 Offer"""
        stmt = select(PartnerOffer).where(PartnerOffer.id == offer_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def _build_checkout_url(self, product: ShopifyProduct) -> str:
        """构建结账 URL"""
        settings = get_settings()
        return (
            f"https://{settings.shopify_shop_domain}/cart/"
            f"{product.shopify_variant_id}:1"
        )


    async def record_click_and_redirect(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        recommendation_item_id: uuid.UUID,
        slot_type: str,
        item_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> RedirectResult:
        """记录点击并返回跳转 URL"""
        commerce_id = uuid.UUID(item_id)

        # 获取跳转 URL
        if slot_type == SlotType.SHOPIFY:
            product = await self._get_product(commerce_id)
            if not product:
                raise ValueError("Product not found")
            redirect_url = self._build_checkout_url(product)
        elif slot_type == SlotType.PARTNER:
            offer = await self._get_offer(commerce_id)
            if not offer:
                raise ValueError("Offer not found")
            redirect_url = offer.redirect_url

            # 更新点击计数
            offer.current_clicks += 1
            await self.db.commit()
        else:
            raise ValueError(f"Invalid slot type: {slot_type}")

        # 记录 CommerceClick
        click = CommerceClick(
            user_id=user_id,
            session_id=session_id,
            recommendation_item_id=recommendation_item_id,
            slot_type=slot_type,
            commerce_id=commerce_id,
            clicked_at=datetime.utcnow(),
        )
        self.db.add(click)

        # 记录 AnalyticsEvent
        event_type = (
            "product_clicked" if slot_type == SlotType.SHOPIFY else "offer_clicked"
        )
        event = AnalyticsEvent(
            user_id=user_id,
            session_id=session_id,
            event_type=event_type,
            event_data={
                "slot_type": slot_type,
                "commerce_id": str(commerce_id),
                "recommendation_item_id": str(recommendation_item_id),
                "redirect_url": redirect_url,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(event)

        await self.db.commit()

        return RedirectResult(redirect_url=redirect_url)


    # ===== 合作商 Offer 管理 =====

    async def create_partner_offer(
        self,
        partner_id: str,
        title: str,
        redirect_url: str,
        payout: Decimal,
        description: Optional[str] = None,
        image_url: Optional[str] = None,
        cap: Optional[int] = None,
    ) -> PartnerOffer:
        """创建合作商 Offer"""
        offer = PartnerOffer(
            partner_id=partner_id,
            title=title,
            description=description,
            image_url=image_url,
            redirect_url=redirect_url,
            payout=payout,
            cap=cap,
            current_clicks=0,
            active=True,
            sponsored=True,  # 必须为 True
        )
        self.db.add(offer)
        await self.db.commit()
        await self.db.refresh(offer)
        return offer

    async def get_partner_offer(
        self,
        offer_id: uuid.UUID,
    ) -> Optional[PartnerOffer]:
        """获取合作商 Offer"""
        return await self._get_offer(offer_id)

    async def list_partner_offers(
        self,
        active_only: bool = True,
    ) -> List[PartnerOffer]:
        """列出合作商 Offers"""
        stmt = select(PartnerOffer)
        if active_only:
            stmt = stmt.where(PartnerOffer.active == True)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_partner_offer(
        self,
        offer_id: uuid.UUID,
        **kwargs: Any,
    ) -> Optional[PartnerOffer]:
        """更新合作商 Offer"""
        offer = await self._get_offer(offer_id)
        if not offer:
            return None

        # 确保 sponsored 始终为 True
        kwargs.pop("sponsored", None)

        for key, value in kwargs.items():
            if hasattr(offer, key):
                setattr(offer, key, value)

        await self.db.commit()
        await self.db.refresh(offer)
        return offer

    async def deactivate_partner_offer(
        self,
        offer_id: uuid.UUID,
    ) -> bool:
        """停用合作商 Offer"""
        offer = await self._get_offer(offer_id)
        if not offer:
            return False
        offer.active = False
        await self.db.commit()
        return True


    # ===== 商品映射管理 =====

    async def create_product_mapping(
        self,
        rec_key: str,
        slot_type: SlotType,
        product_id: Optional[uuid.UUID] = None,
        offer_id: Optional[uuid.UUID] = None,
        priority: int = 0,
    ) -> ProductMapping:
        """创建商品映射"""
        mapping = ProductMapping(
            rec_key=rec_key,
            slot_type=slot_type.value,
            product_id=product_id,
            offer_id=offer_id,
            priority=priority,
            active=True,
        )
        self.db.add(mapping)
        await self.db.commit()
        await self.db.refresh(mapping)
        return mapping

    async def get_mappings_for_rec_key(
        self,
        rec_key: str,
    ) -> List[ProductMapping]:
        """获取 rec_key 的所有映射"""
        stmt = (
            select(ProductMapping)
            .where(ProductMapping.rec_key == rec_key)
            .order_by(ProductMapping.priority.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_mapping_priority(
        self,
        mapping_id: uuid.UUID,
        priority: int,
    ) -> bool:
        """更新映射优先级"""
        stmt = (
            update(ProductMapping)
            .where(ProductMapping.id == mapping_id)
            .values(priority=priority)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def deactivate_mapping(
        self,
        mapping_id: uuid.UUID,
    ) -> bool:
        """停用映射"""
        stmt = (
            update(ProductMapping)
            .where(ProductMapping.id == mapping_id)
            .values(active=False)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0


def create_commerce_service(db: AsyncSession) -> CommerceService:
    """创建商业服务实例"""
    return CommerceService(db=db)

