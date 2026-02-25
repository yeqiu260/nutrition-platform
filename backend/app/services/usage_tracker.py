"""AI 使用量跟踪服务"""

from datetime import date, datetime
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.usage import AIUsage


class UsageTracker:
    """AI 使用量跟踪器"""
    
    def __init__(self, daily_limit: int = 4):
        self.daily_limit = daily_limit
    
    async def check_and_increment(
        self, 
        db: AsyncSession, 
        user_identifier: str
    ) -> dict:
        """
        检查用户今天的使用量并增加计数
        
        Args:
            db: 数据库会话
            user_identifier: 用户标识（IP 或用户 ID）
        
        Returns:
            dict: {
                "allowed": bool,
                "remaining": int,
                "reset_at": datetime
            }
        
        Raises:
            HTTPException: 如果超过每日限制
        """
        today = date.today()
        
        # 查询今天的使用记录
        result = await db.execute(
            select(AIUsage).where(
                AIUsage.user_identifier == user_identifier,
                AIUsage.usage_date == today
            )
        )
        usage = result.scalar_one_or_none()
        
        # 如果没有记录，创建新记录
        if not usage:
            usage = AIUsage(
                id=str(uuid4()),
                user_identifier=user_identifier,
                usage_date=today,
                call_count=1,
                last_call_at=datetime.utcnow()
            )
            db.add(usage)
            await db.commit()
            
            return {
                "allowed": True,
                "remaining": self.daily_limit - 1,
                "reset_at": datetime.combine(today, datetime.max.time())
            }
        
        # 检查是否超过限制
        if usage.call_count >= self.daily_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": f"您今天的 AI 分析次数已用完（{self.daily_limit}次/天）",
                    "daily_limit": self.daily_limit,
                    "used": usage.call_count,
                    "reset_at": datetime.combine(today, datetime.max.time()).isoformat()
                }
            )
        
        # 增加计数
        usage.call_count += 1
        usage.last_call_at = datetime.utcnow()
        await db.commit()
        
        return {
            "allowed": True,
            "remaining": self.daily_limit - usage.call_count,
            "reset_at": datetime.combine(today, datetime.max.time())
        }
    
    async def get_usage(
        self, 
        db: AsyncSession, 
        user_identifier: str
    ) -> dict:
        """
        获取用户今天的使用量（不增加计数）
        
        Returns:
            dict: {
                "used": int,
                "remaining": int,
                "limit": int,
                "reset_at": datetime
            }
        """
        today = date.today()
        
        result = await db.execute(
            select(AIUsage).where(
                AIUsage.user_identifier == user_identifier,
                AIUsage.usage_date == today
            )
        )
        usage = result.scalar_one_or_none()
        
        used = usage.call_count if usage else 0
        
        return {
            "used": used,
            "remaining": max(0, self.daily_limit - used),
            "limit": self.daily_limit,
            "reset_at": datetime.combine(today, datetime.max.time())
        }


# 全局实例
usage_tracker = UsageTracker(daily_limit=10)
