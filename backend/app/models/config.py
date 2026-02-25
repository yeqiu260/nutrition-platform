"""配置相关模型：ConfigVersion、AuditLog"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ConfigVersion(Base):
    """配置版本模型"""

    __tablename__ = "config_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    config_type: Mapped[str] = mapped_column(
        String(50), index=True
    )  # ruleset | weights | prompts | model_config | feature_flags
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(20), default="DRAFT"
    )  # DRAFT | APPROVED | DEPLOYING | ACTIVE | ROLLED_BACK
    content: Mapped[dict] = mapped_column(JSONB)
    rollout_percent: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    change_reason: Mapped[str] = mapped_column(Text)

    # 关系
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="config_version")


class AuditLog(Base):
    """审计日志模型"""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    config_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("config_versions.id"), index=True
    )
    action: Mapped[str] = mapped_column(
        String(50)
    )  # CREATE | UPDATE | APPROVE | DEPLOY | ROLLBACK
    before_value: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    after_value: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    operator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    # 关系
    config_version: Mapped["ConfigVersion"] = relationship(back_populates="audit_logs")
