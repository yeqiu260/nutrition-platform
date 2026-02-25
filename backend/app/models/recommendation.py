"""推荐相关模型：RecommendationSession、RecommendationItem"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RecommendationSession(Base):
    """推荐会话模型"""

    __tablename__ = "recommendation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    health_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("health_profiles.id"), index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="PENDING"
    )  # PENDING | GENERATED | REVIEWED | PUBLISHED
    requires_review: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    user: Mapped["User"] = relationship("User", backref="recommendation_sessions")
    health_profile: Mapped["HealthProfile"] = relationship("HealthProfile", backref="recommendation_sessions")
    items: Mapped[list["RecommendationItem"]] = relationship("RecommendationItem", back_populates="session")
    # analytics_events: Mapped[List["AnalyticsEvent"]] = relationship(
    #     back_populates="session"
    # )
    review_queue: Mapped[Optional["ReviewQueue"]] = relationship(
        "ReviewQueue", back_populates="session", uselist=False
    )


class RecommendationItem(Base):
    """推荐项模型"""

    __tablename__ = "recommendation_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recommendation_sessions.id"), index=True
    )
    rank: Mapped[int] = mapped_column(Integer)  # 1-5
    rec_key: Mapped[str] = mapped_column(String(100))  # 例如 "vitamin_d", "omega_3"
    name: Mapped[dict] = mapped_column(JSONB)  # LocalizedString: {zh_tw, en}
    why_reasons: Mapped[list] = mapped_column(JSONB)  # 3-5条原因
    safety_info: Mapped[dict] = mapped_column(JSONB)  # SafetyInfo
    confidence: Mapped[int] = mapped_column(Integer)  # 0-100
    commerce_type: Mapped[str] = mapped_column(String(20))  # "shopify" | "partner"
    commerce_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    session: Mapped["RecommendationSession"] = relationship("RecommendationSession", back_populates="items")
    # commerce_clicks: Mapped[List["CommerceClick"]] = relationship(
    #     back_populates="recommendation_item"
    # )
