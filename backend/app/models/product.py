"""商品数据模型"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY

from app.core.database import Base


class Product(Base):
    """合作商商品表"""
    __tablename__ = "products"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # 商品基本信息
    name = Column(String(200), nullable=False)  # 商品名称
    description = Column(Text, nullable=True)  # 商品描述
    image_url = Column(String(500), nullable=True)  # 商品图片
    price = Column(Float, nullable=True)  # 价格
    currency = Column(String(10), default="TWD")  # 货币
    
    # 关联信息
    supplement_id = Column(String(50), nullable=False, index=True)  # 关联的补充品ID
    purchase_url = Column(String(500), nullable=False)  # 购买链接
    
    # 合作商信息
    partner_id = Column(UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=False)
    partner_name = Column(String(100), nullable=True)  # 合作商名称（冗余存储）
    
    # 状态
    is_active = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=False)  # 是否审核通过
    sort_order = Column(Integer, default=0)  # 排序权重
    
    # 【商业功能】Cap 限制
    click_cap = Column(Integer, nullable=True)  # 总点击上限（None 表示无限制）
    daily_cap = Column(Integer, nullable=True)  # 每日点击上限
    
    # 【商业功能】地区限制
    allowed_regions = Column(ARRAY(String(10)), nullable=True)  # 允许地区（如 ["TW", "HK"]）
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

