"""后台配置中心服务模块

实现需求 7：后台配置中心
- 7.1 支援配置规则集、权重、提示词、模型配置和功能开关
- 7.2 实现版本化，状态流程为：草稿 → 已审核 → 部署中 → 生效中
- 7.3 记录修改前后差异、操作者、时间戳和修改原因
- 7.4 支援按百分比灰度发布
- 7.5 支援一键回滚到上一个生效版本
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import ConfigVersion, AuditLog


class ConfigType(str, Enum):
    """配置类型枚举"""
    RULESET = "ruleset"
    WEIGHTS = "weights"
    PROMPTS = "prompts"
    MODEL_CONFIG = "model_config"
    FEATURE_FLAGS = "feature_flags"


class ConfigStatus(str, Enum):
    """配置状态枚举
    
    状态流程：DRAFT → APPROVED → DEPLOYING → ACTIVE
    回滚后状态：ROLLED_BACK
    """
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    DEPLOYING = "DEPLOYING"
    ACTIVE = "ACTIVE"
    ROLLED_BACK = "ROLLED_BACK"


class AuditAction(str, Enum):
    """审计操作类型"""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    APPROVE = "APPROVE"
    DEPLOY = "DEPLOY"
    ACTIVATE = "ACTIVATE"
    ROLLBACK = "ROLLBACK"


# 状态转换规则：定义允许的状态转换
VALID_TRANSITIONS = {
    ConfigStatus.DRAFT: [ConfigStatus.APPROVED],
    ConfigStatus.APPROVED: [ConfigStatus.DEPLOYING],
    ConfigStatus.DEPLOYING: [ConfigStatus.ACTIVE],
    ConfigStatus.ACTIVE: [ConfigStatus.ROLLED_BACK],
    ConfigStatus.ROLLED_BACK: [],  # 回滚后不能再转换
}


class ConfigVersionSchema(BaseModel):
    """配置版本 Schema"""
    id: str
    config_type: str
    version: int
    status: str
    content: Dict[str, Any]
    rollout_percent: int
    created_by: str
    created_at: datetime
    change_reason: str


class AuditLogSchema(BaseModel):
    """审计日志 Schema"""
    id: str
    config_version_id: str
    action: str
    before_value: Optional[Dict[str, Any]] = None
    after_value: Optional[Dict[str, Any]] = None
    operator_id: str
    created_at: datetime
    ip_address: Optional[str] = None


class ConfigListResponse(BaseModel):
    """配置列表响应"""
    configs: List[ConfigVersionSchema]
    total: int


class InvalidStateTransitionError(Exception):
    """无效状态转换错误"""
    def __init__(self, current_status: str, target_status: str):
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(
            f"Invalid state transition from {current_status} to {target_status}"
        )


class ConfigNotFoundError(Exception):
    """配置未找到错误"""
    pass


class NoPreviousActiveVersionError(Exception):
    """没有可回滚的版本错误"""
    pass


class ConfigService:
    """后台配置中心服务
    
    实现需求 7：后台配置中心
    - 配置版本管理（草稿、审核、部署、生效）
    - 审计日志记录
    - 灰度发布
    - 一键回滚
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _validate_transition(
        self, current_status: ConfigStatus, target_status: ConfigStatus
    ) -> bool:
        """验证状态转换是否有效
        
        属性 18：配置版本状态机
        状态转换应遵循：DRAFT → APPROVED → DEPLOYING → ACTIVE
        不允许跳跃或逆向转换（回滚除外）
        """
        allowed = VALID_TRANSITIONS.get(current_status, [])
        return target_status in allowed

    async def _create_audit_log(
        self,
        config_version_id: uuid.UUID,
        action: AuditAction,
        operator_id: uuid.UUID,
        before_value: Optional[Dict[str, Any]] = None,
        after_value: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """创建审计日志
        
        属性 19：审计日志完整性
        审计日志应包含 before_value、after_value、operator_id、created_at
        """
        audit_log = AuditLog(
            config_version_id=config_version_id,
            action=action.value,
            before_value=before_value,
            after_value=after_value,
            operator_id=operator_id,
            created_at=datetime.utcnow(),
            ip_address=ip_address,
        )
        self.db.add(audit_log)
        return audit_log

    async def get_active_config(
        self, config_type: ConfigType
    ) -> Optional[ConfigVersion]:
        """获取当前生效配置
        
        Args:
            config_type: 配置类型
            
        Returns:
            当前生效的配置版本，如果没有则返回 None
        """
        stmt = (
            select(ConfigVersion)
            .where(
                and_(
                    ConfigVersion.config_type == config_type.value,
                    ConfigVersion.status == ConfigStatus.ACTIVE.value,
                )
            )
            .order_by(desc(ConfigVersion.version))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_config_by_id(
        self, version_id: uuid.UUID
    ) -> Optional[ConfigVersion]:
        """根据 ID 获取配置版本"""
        stmt = select(ConfigVersion).where(ConfigVersion.id == version_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_version_number(self, config_type: ConfigType) -> int:
        """获取最新版本号"""
        stmt = (
            select(ConfigVersion.version)
            .where(ConfigVersion.config_type == config_type.value)
            .order_by(desc(ConfigVersion.version))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        version = result.scalar_one_or_none()
        return version if version else 0

    async def create_draft(
        self,
        config_type: ConfigType,
        content: Dict[str, Any],
        change_reason: str,
        created_by: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> ConfigVersion:
        """创建草稿配置
        
        需求 7.1：支援配置规则集、权重、提示词、模型配置和功能开关
        需求 7.2：状态流程从草稿开始
        
        Args:
            config_type: 配置类型
            content: 配置内容
            change_reason: 修改原因
            created_by: 创建者 ID
            ip_address: IP 地址
            
        Returns:
            创建的配置版本
        """
        # 获取下一个版本号
        latest_version = await self.get_latest_version_number(config_type)
        new_version = latest_version + 1

        # 创建配置版本
        config = ConfigVersion(
            config_type=config_type.value,
            version=new_version,
            status=ConfigStatus.DRAFT.value,
            content=content,
            rollout_percent=0,
            created_by=created_by,
            created_at=datetime.utcnow(),
            change_reason=change_reason,
        )
        self.db.add(config)
        await self.db.flush()

        # 创建审计日志
        await self._create_audit_log(
            config_version_id=config.id,
            action=AuditAction.CREATE,
            operator_id=created_by,
            before_value=None,
            after_value={"content": content, "change_reason": change_reason},
            ip_address=ip_address,
        )

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def approve_config(
        self,
        version_id: uuid.UUID,
        approver_id: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> ConfigVersion:
        """审核配置
        
        需求 7.2：状态从 DRAFT 转换到 APPROVED
        
        Args:
            version_id: 配置版本 ID
            approver_id: 审核者 ID
            ip_address: IP 地址
            
        Returns:
            更新后的配置版本
            
        Raises:
            ConfigNotFoundError: 配置不存在
            InvalidStateTransitionError: 无效的状态转换
        """
        config = await self.get_config_by_id(version_id)
        if not config:
            raise ConfigNotFoundError(f"Config version {version_id} not found")

        current_status = ConfigStatus(config.status)
        target_status = ConfigStatus.APPROVED

        if not self._validate_transition(current_status, target_status):
            raise InvalidStateTransitionError(
                current_status.value, target_status.value
            )

        before_status = config.status
        config.status = target_status.value

        # 创建审计日志
        await self._create_audit_log(
            config_version_id=config.id,
            action=AuditAction.APPROVE,
            operator_id=approver_id,
            before_value={"status": before_status},
            after_value={"status": target_status.value},
            ip_address=ip_address,
        )

        await self.db.commit()
        await self.db.refresh(config)
        return config


    async def deploy_config(
        self,
        version_id: uuid.UUID,
        rollout_percent: int,
        operator_id: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> ConfigVersion:
        """部署配置
        
        需求 7.2：状态从 APPROVED 转换到 DEPLOYING
        需求 7.4：支援按百分比灰度发布
        
        Args:
            version_id: 配置版本 ID
            rollout_percent: 灰度发布百分比 (0-100)
            operator_id: 操作者 ID
            ip_address: IP 地址
            
        Returns:
            更新后的配置版本
        """
        config = await self.get_config_by_id(version_id)
        if not config:
            raise ConfigNotFoundError(f"Config version {version_id} not found")

        current_status = ConfigStatus(config.status)
        target_status = ConfigStatus.DEPLOYING

        if not self._validate_transition(current_status, target_status):
            raise InvalidStateTransitionError(
                current_status.value, target_status.value
            )

        before_value = {
            "status": config.status,
            "rollout_percent": config.rollout_percent,
        }
        
        config.status = target_status.value
        config.rollout_percent = max(0, min(100, rollout_percent))  # 确保在 0-100 范围内

        # 创建审计日志
        await self._create_audit_log(
            config_version_id=config.id,
            action=AuditAction.DEPLOY,
            operator_id=operator_id,
            before_value=before_value,
            after_value={
                "status": target_status.value,
                "rollout_percent": config.rollout_percent,
            },
            ip_address=ip_address,
        )

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def activate_config(
        self,
        version_id: uuid.UUID,
        operator_id: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> ConfigVersion:
        """激活配置（从 DEPLOYING 到 ACTIVE）
        
        需求 7.2：状态从 DEPLOYING 转换到 ACTIVE
        
        激活新配置时，会将同类型的其他 ACTIVE 配置标记为 ROLLED_BACK
        
        Args:
            version_id: 配置版本 ID
            operator_id: 操作者 ID
            ip_address: IP 地址
            
        Returns:
            更新后的配置版本
        """
        config = await self.get_config_by_id(version_id)
        if not config:
            raise ConfigNotFoundError(f"Config version {version_id} not found")

        current_status = ConfigStatus(config.status)
        target_status = ConfigStatus.ACTIVE

        if not self._validate_transition(current_status, target_status):
            raise InvalidStateTransitionError(
                current_status.value, target_status.value
            )

        # 将同类型的其他 ACTIVE 配置标记为 ROLLED_BACK
        stmt = select(ConfigVersion).where(
            and_(
                ConfigVersion.config_type == config.config_type,
                ConfigVersion.status == ConfigStatus.ACTIVE.value,
                ConfigVersion.id != config.id,
            )
        )
        result = await self.db.execute(stmt)
        old_active_configs = result.scalars().all()

        for old_config in old_active_configs:
            old_config.status = ConfigStatus.ROLLED_BACK.value
            await self._create_audit_log(
                config_version_id=old_config.id,
                action=AuditAction.ROLLBACK,
                operator_id=operator_id,
                before_value={"status": ConfigStatus.ACTIVE.value},
                after_value={"status": ConfigStatus.ROLLED_BACK.value},
                ip_address=ip_address,
            )

        before_status = config.status
        config.status = target_status.value
        config.rollout_percent = 100  # 激活时设为 100%

        # 创建审计日志
        await self._create_audit_log(
            config_version_id=config.id,
            action=AuditAction.ACTIVATE,
            operator_id=operator_id,
            before_value={"status": before_status},
            after_value={"status": target_status.value, "rollout_percent": 100},
            ip_address=ip_address,
        )

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def rollback_config(
        self,
        config_type: ConfigType,
        operator_id: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> ConfigVersion:
        """回滚配置到上一个生效版本
        
        需求 7.5：支援一键回滚到上一个生效版本
        属性 20：配置回滚正确性 - 当前生效版本应变为上一个 ACTIVE 版本
        
        Args:
            config_type: 配置类型
            operator_id: 操作者 ID
            ip_address: IP 地址
            
        Returns:
            回滚后的生效配置版本
            
        Raises:
            NoPreviousActiveVersionError: 没有可回滚的版本
        """
        # 获取当前 ACTIVE 配置
        current_active = await self.get_active_config(config_type)
        
        # 查找上一个 ROLLED_BACK 版本（按版本号降序，取最新的）
        stmt = (
            select(ConfigVersion)
            .where(
                and_(
                    ConfigVersion.config_type == config_type.value,
                    ConfigVersion.status == ConfigStatus.ROLLED_BACK.value,
                )
            )
            .order_by(desc(ConfigVersion.version))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        previous_version = result.scalar_one_or_none()

        if not previous_version:
            raise NoPreviousActiveVersionError(
                f"No previous active version found for {config_type.value}"
            )

        # 将当前 ACTIVE 配置标记为 ROLLED_BACK
        if current_active:
            current_active.status = ConfigStatus.ROLLED_BACK.value
            await self._create_audit_log(
                config_version_id=current_active.id,
                action=AuditAction.ROLLBACK,
                operator_id=operator_id,
                before_value={"status": ConfigStatus.ACTIVE.value},
                after_value={"status": ConfigStatus.ROLLED_BACK.value},
                ip_address=ip_address,
            )

        # 将上一个版本重新激活
        previous_version.status = ConfigStatus.ACTIVE.value
        previous_version.rollout_percent = 100

        await self._create_audit_log(
            config_version_id=previous_version.id,
            action=AuditAction.ACTIVATE,
            operator_id=operator_id,
            before_value={"status": ConfigStatus.ROLLED_BACK.value},
            after_value={"status": ConfigStatus.ACTIVE.value, "rollout_percent": 100},
            ip_address=ip_address,
        )

        await self.db.commit()
        await self.db.refresh(previous_version)
        return previous_version


    async def get_config_history(
        self,
        config_type: ConfigType,
        page: int = 1,
        page_size: int = 20,
    ) -> ConfigListResponse:
        """获取配置版本历史
        
        Args:
            config_type: 配置类型
            page: 页码
            page_size: 每页数量
            
        Returns:
            配置版本列表
        """
        # 查询总数
        count_stmt = select(ConfigVersion).where(
            ConfigVersion.config_type == config_type.value
        )
        count_result = await self.db.execute(count_stmt)
        total = len(count_result.scalars().all())

        # 分页查询
        offset = (page - 1) * page_size
        stmt = (
            select(ConfigVersion)
            .where(ConfigVersion.config_type == config_type.value)
            .order_by(desc(ConfigVersion.version))
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        configs = result.scalars().all()

        return ConfigListResponse(
            configs=[
                ConfigVersionSchema(
                    id=str(c.id),
                    config_type=c.config_type,
                    version=c.version,
                    status=c.status,
                    content=c.content,
                    rollout_percent=c.rollout_percent,
                    created_by=str(c.created_by),
                    created_at=c.created_at,
                    change_reason=c.change_reason,
                )
                for c in configs
            ],
            total=total,
        )

    async def get_audit_logs(
        self,
        config_version_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> List[AuditLogSchema]:
        """获取配置版本的审计日志
        
        需求 7.3：记录修改前后差异、操作者、时间戳和修改原因
        
        Args:
            config_version_id: 配置版本 ID
            page: 页码
            page_size: 每页数量
            
        Returns:
            审计日志列表
        """
        offset = (page - 1) * page_size
        stmt = (
            select(AuditLog)
            .where(AuditLog.config_version_id == config_version_id)
            .order_by(desc(AuditLog.created_at))
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        logs = result.scalars().all()

        return [
            AuditLogSchema(
                id=str(log.id),
                config_version_id=str(log.config_version_id),
                action=log.action,
                before_value=log.before_value,
                after_value=log.after_value,
                operator_id=str(log.operator_id),
                created_at=log.created_at,
                ip_address=log.ip_address,
            )
            for log in logs
        ]

    async def get_all_audit_logs_by_type(
        self,
        config_type: ConfigType,
        page: int = 1,
        page_size: int = 50,
    ) -> List[AuditLogSchema]:
        """获取某类型配置的所有审计日志
        
        Args:
            config_type: 配置类型
            page: 页码
            page_size: 每页数量
            
        Returns:
            审计日志列表
        """
        offset = (page - 1) * page_size
        stmt = (
            select(AuditLog)
            .join(ConfigVersion, AuditLog.config_version_id == ConfigVersion.id)
            .where(ConfigVersion.config_type == config_type.value)
            .order_by(desc(AuditLog.created_at))
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        logs = result.scalars().all()

        return [
            AuditLogSchema(
                id=str(log.id),
                config_version_id=str(log.config_version_id),
                action=log.action,
                before_value=log.before_value,
                after_value=log.after_value,
                operator_id=str(log.operator_id),
                created_at=log.created_at,
                ip_address=log.ip_address,
            )
            for log in logs
        ]

    def should_apply_config(
        self,
        config: ConfigVersion,
        user_id: uuid.UUID,
    ) -> bool:
        """判断是否应该对用户应用配置（灰度发布逻辑）
        
        需求 7.4：支援按百分比灰度发布
        
        使用用户 ID 的哈希值来确定用户是否在灰度范围内，
        确保同一用户始终得到一致的结果。
        
        Args:
            config: 配置版本
            user_id: 用户 ID
            
        Returns:
            是否应该应用该配置
        """
        if config.rollout_percent >= 100:
            return True
        if config.rollout_percent <= 0:
            return False

        # 使用用户 ID 的哈希值来确定是否在灰度范围内
        user_hash = hash(str(user_id)) % 100
        return user_hash < config.rollout_percent


def create_config_service(db: AsyncSession) -> ConfigService:
    """创建配置服务实例"""
    return ConfigService(db=db)
