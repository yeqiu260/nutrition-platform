"""用户同意服务"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserConsent


class ConsentService:
    """用户同意服务"""
    
    # 当前版本号
    CURRENT_VERSION = "v1.0"
    
    # 同意类型
    CONSENT_TYPES = {
        "terms": "服务条款",
        "privacy": "隐私政策",
        "health_data": "健康数据使用",
        "marketing": "营销推广"
    }
    
    async def record_consent(
        self,
        db: AsyncSession,
        user_id: Optional[UUID],
        consent_type: str,
        is_agreed: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        version: Optional[str] = None
    ) -> UserConsent:
        """
        记录用户同意
        
        Args:
            user_id: 用户 ID（可为空，用于匿名用户）
            consent_type: 同意类型
            is_agreed: 是否同意
            ip_address: IP 地址
            user_agent: User Agent
            version: 版本号（默认使用当前版本）
        
        Returns:
            UserConsent 对象
        """
        if consent_type not in self.CONSENT_TYPES:
            raise ValueError(f"无效的同意类型: {consent_type}")
        
        consent = UserConsent(
            id=uuid4(),
            user_id=user_id,
            consent_type=consent_type,
            is_agreed=is_agreed,
            version=version or self.CURRENT_VERSION,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.utcnow()
        )
        
        db.add(consent)
        await db.commit()
        await db.refresh(consent)
        
        return consent
    
    async def record_all_consents(
        self,
        db: AsyncSession,
        user_id: Optional[UUID],
        consents: dict,  # {consent_type: is_agreed}
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> List[UserConsent]:
        """
        批量记录用户同意
        
        Args:
            user_id: 用户 ID
            consents: 同意字典 {consent_type: is_agreed}
            ip_address: IP 地址
            user_agent: User Agent
        
        Returns:
            UserConsent 对象列表
        """
        consent_records = []
        
        for consent_type, is_agreed in consents.items():
            consent = await self.record_consent(
                db=db,
                user_id=user_id,
                consent_type=consent_type,
                is_agreed=is_agreed,
                ip_address=ip_address,
                user_agent=user_agent
            )
            consent_records.append(consent)
        
        return consent_records
    
    async def get_user_consents(
        self,
        db: AsyncSession,
        user_id: UUID,
        consent_type: Optional[str] = None
    ) -> List[UserConsent]:
        """
        获取用户的同意记录
        
        Args:
            user_id: 用户 ID
            consent_type: 同意类型（可选，不指定则返回所有）
        
        Returns:
            UserConsent 对象列表
        """
        query = select(UserConsent).where(
            UserConsent.user_id == user_id,
            UserConsent.revoked_at.is_(None)
        )
        
        if consent_type:
            query = query.where(UserConsent.consent_type == consent_type)
        
        query = query.order_by(UserConsent.created_at.desc())
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def check_consent(
        self,
        db: AsyncSession,
        user_id: UUID,
        consent_type: str,
        required_version: Optional[str] = None
    ) -> bool:
        """
        检查用户是否同意某项条款
        
        Args:
            user_id: 用户 ID
            consent_type: 同意类型
            required_version: 要求的版本号（可选）
        
        Returns:
            True if agreed, False otherwise
        """
        query = select(UserConsent).where(
            UserConsent.user_id == user_id,
            UserConsent.consent_type == consent_type,
            UserConsent.is_agreed == True,
            UserConsent.revoked_at.is_(None)
        )
        
        if required_version:
            query = query.where(UserConsent.version == required_version)
        
        query = query.order_by(UserConsent.created_at.desc()).limit(1)
        
        result = await db.execute(query)
        consent = result.scalar_one_or_none()
        
        return consent is not None
    
    async def revoke_consent(
        self,
        db: AsyncSession,
        user_id: UUID,
        consent_type: str
    ) -> bool:
        """
        撤销用户同意
        
        Args:
            user_id: 用户 ID
            consent_type: 同意类型
        
        Returns:
            True if revoked, False if not found
        """
        result = await db.execute(
            select(UserConsent).where(
                UserConsent.user_id == user_id,
                UserConsent.consent_type == consent_type,
                UserConsent.revoked_at.is_(None)
            ).order_by(UserConsent.created_at.desc()).limit(1)
        )
        consent = result.scalar_one_or_none()
        
        if not consent:
            return False
        
        consent.revoked_at = datetime.utcnow()
        await db.commit()
        
        return True
    
    async def get_required_consents(self) -> dict:
        """
        获取必需的同意项
        
        Returns:
            {consent_type: description}
        """
        return {
            "terms": self.CONSENT_TYPES["terms"],
            "privacy": self.CONSENT_TYPES["privacy"],
            "health_data": self.CONSENT_TYPES["health_data"]
        }
    
    async def get_optional_consents(self) -> dict:
        """
        获取可选的同意项
        
        Returns:
            {consent_type: description}
        """
        return {
            "marketing": self.CONSENT_TYPES["marketing"]
        }


# 全局实例
consent_service = ConsentService()
