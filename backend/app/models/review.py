"""审核相关模型：ReviewQueue"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ReviewQueue(Base):
    """审核队列模型"""

    __tablename__ = "review_queue"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recommendation_sessions.id"), unique=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="PENDING"
    )  # PENDING | IN_REVIEW | APPROVED | REJECTED
    risk_level: Mapped[str] = mapped_column(
        String(20), default="MEDIUM"
    )  # LOW | MEDIUM | HIGH | CRITICAL
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # session: Mapped["RecommendationSession"] = relationship(back_populates="review_queue")
    session: Mapped["RecommendationSession"] = relationship("RecommendationSession", back_populates="review_queue")
