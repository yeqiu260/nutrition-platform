"""用户历史记录和收藏模型"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class QuizHistory(Base):
    """问卷历史记录"""
    __tablename__ = "quiz_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String(100), nullable=False, unique=True, index=True)
    
    # 问卷数据
    answers = Column(JSON, nullable=False)  # 问卷答案
    health_data = Column(JSON, nullable=True)  # 化验值数据
    
    # AI 推荐结果
    recommendations = Column(JSON, nullable=False)  # AI 推荐结果
    ai_generated = Column(Boolean, default=True)  # 是否 AI 生成
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<QuizHistory {self.session_id}>"


class FavoriteProduct(Base):
    """用户收藏的商品"""
    __tablename__ = "favorite_products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    
    # 收藏时的备注
    note = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<FavoriteProduct user={self.user_id} product={self.product_id}>"
