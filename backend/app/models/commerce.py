"""商业相关模型：Product、ProductMapping、PartnerOffer、CommerceClick"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.recommendation import RecommendationItem, RecommendationSession
    from app.models.user import User


class ShopifyProduct(Base):
    """Shopify 商品模型 (已废弃)"""

    __tablename__ = "shopify_products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    shopify_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    shopify_variant_id: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(500))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(10), default="TWD")
    image_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    mappings: Mapped[List["ProductMapping"]] = relationship(
        back_populates="shopify_product",
        foreign_keys="ProductMapping.product_id",
    )


class PartnerOffer(Base):
    """合作商 Offer 模型"""

    __tablename__ = "partner_offers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    partner_id: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    redirect_url: Mapped[str] = mapped_column(String(2000))
    payout: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    cap: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_clicks: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sponsored: Mapped[bool] = mapped_column(Boolean, default=True)  # 必须为 True

    # 关系
    mappings: Mapped[List["ProductMapping"]] = relationship(
        back_populates="offer",
        foreign_keys="ProductMapping.offer_id",
    )


class ProductMapping(Base):
    """商品映射模型 - 将 rec_key 映射到商品或 Offer"""

    __tablename__ = "product_mappings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rec_key: Mapped[str] = mapped_column(String(100), index=True)
    slot_type: Mapped[str] = mapped_column(String(20))  # "shopify" | "partner"
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shopify_products.id"), nullable=True
    )
    offer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partner_offers.id"), nullable=True
    )
    priority: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # 关系
    shopify_product: Mapped[Optional["ShopifyProduct"]] = relationship(
        back_populates="mappings",
        foreign_keys=[product_id],
    )
    offer: Mapped[Optional["PartnerOffer"]] = relationship(
        back_populates="mappings",
        foreign_keys=[offer_id],
    )


class CommerceClick(Base):
    """商品点击追踪模型"""

    __tablename__ = "commerce_clicks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recommendation_sessions.id"), index=True
    )
    recommendation_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recommendation_items.id"), index=True
    )
    slot_type: Mapped[str] = mapped_column(String(20))  # "shopify" | "partner"
    commerce_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    clicked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    converted: Mapped[bool] = mapped_column(Boolean, default=False)

    # 注意：暂时移除关系定义以避免循环导入问题
    # user: Mapped["User"] = relationship()
    # session: Mapped["RecommendationSession"] = relationship()
    # recommendation_item: Mapped["RecommendationItem"] = relationship(
    #     back_populates="commerce_clicks"
    # )
