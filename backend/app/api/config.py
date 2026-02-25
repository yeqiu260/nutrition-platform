"""后台配置中心 API 路由

实现需求 7：后台配置中心
- 7.1 支援配置规则集、权重、提示词、模型配置和功能开关
- 7.2 实现版本化，状态流程为：草稿 → 已审核 → 部署中 → 生效中
- 7.3 记录修改前后差异、操作者、时间戳和修改原因
- 7.4 支援按百分比灰度发布
- 7.5 支援一键回滚到上一个生效版本
"""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.config import (
    ConfigService,
    ConfigType,
    ConfigStatus,
    ConfigVersionSchema,
    AuditLogSchema,
    ConfigListResponse,
    InvalidStateTransitionError,
    ConfigNotFoundError,
    NoPreviousActiveVersionError,
    create_config_service,
)

router = APIRouter(prefix="/config", tags=["config"])


# ===== 请求/响应模型 =====

class CreateDraftRequest(BaseModel):
    """创建草稿请求"""
    config_type: ConfigType
    content: Dict[str, Any]
    change_reason: str = Field(..., min_length=1, max_length=500)


class DeployConfigRequest(BaseModel):
    """部署配置请求"""
    rollout_percent: int = Field(..., ge=0, le=100)


class ConfigResponse(BaseModel):
    """配置响应"""
    config: ConfigVersionSchema


class AuditLogsResponse(BaseModel):
    """审计日志响应"""
    logs: List[AuditLogSchema]


# ===== 辅助函数 =====

def get_client_ip(request: Request) -> Optional[str]:
    """获取客户端 IP"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


# ===== API 端点 =====

@router.post("/draft", response_model=ConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_draft(
    request: Request,
    body: CreateDraftRequest,
    operator_id: str,  # 实际应从认证中间件获取
    db: AsyncSession = Depends(get_db),
):
    """创建配置草稿
    
    需求 7.1：支援配置规则集、权重、提示词、模型配置和功能开关
    """
    service = create_config_service(db)
    
    try:
        config = await service.create_draft(
            config_type=body.config_type,
            content=body.content,
            change_reason=body.change_reason,
            created_by=uuid.UUID(operator_id),
            ip_address=get_client_ip(request),
        )
        return ConfigResponse(
            config=ConfigVersionSchema(
                id=str(config.id),
                config_type=config.config_type,
                version=config.version,
                status=config.status,
                content=config.content,
                rollout_percent=config.rollout_percent,
                created_by=str(config.created_by),
                created_at=config.created_at,
                change_reason=config.change_reason,
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/{version_id}/approve", response_model=ConfigResponse)
async def approve_config(
    request: Request,
    version_id: uuid.UUID,
    operator_id: str,  # 实际应从认证中间件获取
    db: AsyncSession = Depends(get_db),
):
    """审核配置
    
    需求 7.2：状态从 DRAFT 转换到 APPROVED
    """
    service = create_config_service(db)
    
    try:
        config = await service.approve_config(
            version_id=version_id,
            approver_id=uuid.UUID(operator_id),
            ip_address=get_client_ip(request),
        )
        return ConfigResponse(
            config=ConfigVersionSchema(
                id=str(config.id),
                config_type=config.config_type,
                version=config.version,
                status=config.status,
                content=config.content,
                rollout_percent=config.rollout_percent,
                created_by=str(config.created_by),
                created_at=config.created_at,
                change_reason=config.change_reason,
            )
        )
    except ConfigNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Config version {version_id} not found",
        )
    except InvalidStateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid state transition: {e.current_status} -> {e.target_status}",
        )


@router.post("/{version_id}/deploy", response_model=ConfigResponse)
async def deploy_config(
    request: Request,
    version_id: uuid.UUID,
    body: DeployConfigRequest,
    operator_id: str,  # 实际应从认证中间件获取
    db: AsyncSession = Depends(get_db),
):
    """部署配置
    
    需求 7.2：状态从 APPROVED 转换到 DEPLOYING
    需求 7.4：支援按百分比灰度发布
    """
    service = create_config_service(db)
    
    try:
        config = await service.deploy_config(
            version_id=version_id,
            rollout_percent=body.rollout_percent,
            operator_id=uuid.UUID(operator_id),
            ip_address=get_client_ip(request),
        )
        return ConfigResponse(
            config=ConfigVersionSchema(
                id=str(config.id),
                config_type=config.config_type,
                version=config.version,
                status=config.status,
                content=config.content,
                rollout_percent=config.rollout_percent,
                created_by=str(config.created_by),
                created_at=config.created_at,
                change_reason=config.change_reason,
            )
        )
    except ConfigNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Config version {version_id} not found",
        )
    except InvalidStateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid state transition: {e.current_status} -> {e.target_status}",
        )


@router.post("/{version_id}/activate", response_model=ConfigResponse)
async def activate_config(
    request: Request,
    version_id: uuid.UUID,
    operator_id: str,  # 实际应从认证中间件获取
    db: AsyncSession = Depends(get_db),
):
    """激活配置
    
    需求 7.2：状态从 DEPLOYING 转换到 ACTIVE
    """
    service = create_config_service(db)
    
    try:
        config = await service.activate_config(
            version_id=version_id,
            operator_id=uuid.UUID(operator_id),
            ip_address=get_client_ip(request),
        )
        return ConfigResponse(
            config=ConfigVersionSchema(
                id=str(config.id),
                config_type=config.config_type,
                version=config.version,
                status=config.status,
                content=config.content,
                rollout_percent=config.rollout_percent,
                created_by=str(config.created_by),
                created_at=config.created_at,
                change_reason=config.change_reason,
            )
        )
    except ConfigNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Config version {version_id} not found",
        )
    except InvalidStateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid state transition: {e.current_status} -> {e.target_status}",
        )


@router.post("/{config_type}/rollback", response_model=ConfigResponse)
async def rollback_config(
    request: Request,
    config_type: ConfigType,
    operator_id: str,  # 实际应从认证中间件获取
    db: AsyncSession = Depends(get_db),
):
    """回滚配置到上一个生效版本
    
    需求 7.5：支援一键回滚到上一个生效版本
    """
    service = create_config_service(db)
    
    try:
        config = await service.rollback_config(
            config_type=config_type,
            operator_id=uuid.UUID(operator_id),
            ip_address=get_client_ip(request),
        )
        return ConfigResponse(
            config=ConfigVersionSchema(
                id=str(config.id),
                config_type=config.config_type,
                version=config.version,
                status=config.status,
                content=config.content,
                rollout_percent=config.rollout_percent,
                created_by=str(config.created_by),
                created_at=config.created_at,
                change_reason=config.change_reason,
            )
        )
    except NoPreviousActiveVersionError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No previous active version found for {config_type.value}",
        )


@router.get("/{config_type}/active", response_model=ConfigResponse)
async def get_active_config(
    config_type: ConfigType,
    db: AsyncSession = Depends(get_db),
):
    """获取当前生效配置"""
    service = create_config_service(db)
    
    config = await service.get_active_config(config_type)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active config found for {config_type.value}",
        )
    
    return ConfigResponse(
        config=ConfigVersionSchema(
            id=str(config.id),
            config_type=config.config_type,
            version=config.version,
            status=config.status,
            content=config.content,
            rollout_percent=config.rollout_percent,
            created_by=str(config.created_by),
            created_at=config.created_at,
            change_reason=config.change_reason,
        )
    )


@router.get("/{config_type}/history", response_model=ConfigListResponse)
async def get_config_history(
    config_type: ConfigType,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """获取配置版本历史"""
    service = create_config_service(db)
    return await service.get_config_history(config_type, page, page_size)


@router.get("/{version_id}/audit-logs", response_model=AuditLogsResponse)
async def get_audit_logs(
    version_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """获取配置版本的审计日志
    
    需求 7.3：记录修改前后差异、操作者、时间戳和修改原因
    """
    service = create_config_service(db)
    logs = await service.get_audit_logs(version_id, page, page_size)
    return AuditLogsResponse(logs=logs)


@router.get("/{config_type}/all-audit-logs", response_model=AuditLogsResponse)
async def get_all_audit_logs_by_type(
    config_type: ConfigType,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """获取某类型配置的所有审计日志"""
    service = create_config_service(db)
    logs = await service.get_all_audit_logs_by_type(config_type, page, page_size)
    return AuditLogsResponse(logs=logs)
