"""分析相关模型：AnalyticsEvent"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnalyticsEvent(Base):
    """分析事件模型"""

    __tablename__ = "analytics_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recommendation_sessions.id"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(50), index=True
    )  # quiz_completed | report_uploaded | report_extracted | recommendation_generated | product_clicked | offer_clicked | purchase_completed
    event_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 注意：暂时移除关系定义以避免循环导入问题
    # 如果需要使用这些关系，请确保所有相关模型都已正确定义
    # user: Mapped["User"] = relationship()
    # session: Mapped[Optional["RecommendationSession"]] = relationship(
    #     back_populates="analytics_events"
    # )

