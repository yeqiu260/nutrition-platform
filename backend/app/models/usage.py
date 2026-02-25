"""用户使用量跟踪模型"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Date, Index
from app.core.database import Base


class AIUsage(Base):
    """AI 调用使用量记录"""
    
    __tablename__ = "ai_usage"
    
    id = Column(String, primary_key=True)
    user_identifier = Column(String, nullable=False, index=True)  # IP 或用户 ID
    usage_date = Column(Date, nullable=False, index=True)  # 使用日期
    call_count = Column(Integer, default=0)  # 当天调用次数
    last_call_at = Column(DateTime, nullable=True)  # 最后调用时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 复合索引：快速查询某用户某天的使用量
    __table_args__ = (
        Index('idx_user_date', 'user_identifier', 'usage_date'),
    )
