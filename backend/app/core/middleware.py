"""应用中间件"""

from typing import Callable, Optional
from uuid import UUID

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.redis import get_redis
from app.core.security import (
    Role,
    Permission,
    RBACService,
    SecurityContext,
    ROLE_PERMISSIONS,
)


class ConsentCheckMiddleware(BaseHTTPMiddleware):
    """同意检查中间件 - 验证用户是否已提供必要同意"""

    # 不需要检查同意的路由
    EXEMPT_PATHS = {
        "/",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/auth",
        "/api/quiz",
        "/api/debug",
        "/api/admin",
        "/api/report",
        "/api/products",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """处理请求"""
        # OPTIONS 请求直接放行（CORS 预检）
        if request.method == "OPTIONS":
            return await call_next(request)
        
        path = request.url.path
        
        # 检查是否在豁免列表中
        if self._is_exempt(path):
            return await call_next(request)
        
        # 检查是否需要验证同意
        # 从 token 中提取 user_id
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid authorization header"},
            )

        token = auth_header[7:]  # 移除 "Bearer " 前缀

        # 验证 token 并检查同意
        from app.services.auth import AuthService
        from app.core.database import async_session_maker

        async with async_session_maker() as db:
            redis = await get_redis()
            auth_service = AuthService(db, redis)
            user_id = auth_service.verify_jwt_token(token)

            if not user_id:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid token"},
                )

            # 检查同意状态
            consent_status = await auth_service.check_consent(UUID(user_id))
            if not consent_status.health_data_consented:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Health data consent required"},
                )

        response = await call_next(request)
        return response

    def _is_exempt(self, path: str) -> bool:
        """检查路由是否豁免同意检查"""
        for exempt_path in self.EXEMPT_PATHS:
            if path == exempt_path or path.startswith(exempt_path + "/"):
                return True
        return False


class RBACMiddleware(BaseHTTPMiddleware):
    """RBAC 权限检查中间件"""

    # 路由权限映射
    ROUTE_PERMISSIONS: dict[str, list[Permission]] = {
        # 配置管理路由
        "/api/config": [Permission.CONFIG_READ],
        "/api/config/deploy": [Permission.CONFIG_DEPLOY],
        "/api/config/rollback": [Permission.CONFIG_ROLLBACK],
        
        # 审核队列路由
        "/api/review": [Permission.REVIEW_READ],
        
        # 分析数据路由
        "/api/analytics": [Permission.ANALYTICS_READ],
        "/api/analytics/export": [Permission.ANALYTICS_EXPORT],
        
        # 商品管理路由
        "/api/commerce/admin": [Permission.PRODUCT_WRITE],
        "/api/commerce/sync": [Permission.PRODUCT_SYNC],
    }

    # 不需要权限检查的路由（公开或用户自有资源）
    EXEMPT_PATHS = {
        "/",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/auth",
        "/api/questionnaire",
        "/api/report",
        "/api/recommendations",
        "/api/commerce/products",
        "/api/commerce/out",
        "/api/quiz",
        "/api/debug",
        "/api/admin",
        "/api/products",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """处理请求"""
        # OPTIONS 请求直接放行（CORS 预检）
        if request.method == "OPTIONS":
            return await call_next(request)
        
        path = request.url.path
        
        # 检查是否需要权限验证
        if self._is_exempt(path):
            return await call_next(request)
        
        # 获取所需权限
        required_permissions = self._get_required_permissions(path)
        if not required_permissions:
            return await call_next(request)
        
        # 获取用户角色
        security_ctx = await self._get_security_context(request)
        if not security_ctx:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"},
            )
        
        # 检查权限
        has_permission = RBACService.has_any_permission(
            security_ctx.role,
            required_permissions
        )
        
        if not has_permission:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": f"Permission denied: one of {[p.value for p in required_permissions]} required"
                },
            )
        
        # 将安全上下文存储到请求状态
        request.state.security_context = security_ctx
        
        return await call_next(request)

    def _is_exempt(self, path: str) -> bool:
        """检查路由是否豁免权限检查"""
        for exempt_path in self.EXEMPT_PATHS:
            if path == exempt_path or path.startswith(exempt_path + "/"):
                return True
        return False

    def _get_required_permissions(self, path: str) -> list[Permission]:
        """获取路由所需权限"""
        for route_prefix, permissions in self.ROUTE_PERMISSIONS.items():
            if path.startswith(route_prefix):
                return permissions
        return []

    async def _get_security_context(self, request: Request) -> Optional[SecurityContext]:
        """从请求中获取安全上下文"""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header[7:]
        
        from app.services.auth import AuthService
        from app.core.database import async_session_maker
        from sqlalchemy import select
        from app.models.user import User
        
        async with async_session_maker() as db:
            redis = await get_redis()
            auth_service = AuthService(db, redis)
            user_id = auth_service.verify_jwt_token(token)
            
            if not user_id:
                return None
            
            # 获取用户角色
            stmt = select(User).where(User.id == UUID(user_id))
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            role = Role(user.role) if user.role in [r.value for r in Role] else Role.USER
            permissions = ROLE_PERMISSIONS.get(role, set())
            
            ip_address = request.client.host if request.client else ""
            
            return SecurityContext(
                user_id=UUID(user_id),
                role=role,
                permissions=permissions,
                ip_address=ip_address,
            )


async def get_security_context(request: Request) -> Optional[SecurityContext]:
    """
    FastAPI 依赖项 - 获取当前请求的安全上下文
    
    Usage:
        @router.get("/protected")
        async def protected_route(
            security_ctx: SecurityContext = Depends(get_security_context)
        ):
            ...
    """
    # 首先尝试从请求状态获取（由中间件设置）
    if hasattr(request.state, 'security_context'):
        return request.state.security_context
    
    # 否则手动解析
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header[7:]
    
    from app.services.auth import AuthService
    from app.core.database import async_session_maker
    from sqlalchemy import select
    from app.models.user import User
    
    async with async_session_maker() as db:
        redis = await get_redis()
        auth_service = AuthService(db, redis)
        user_id = auth_service.verify_jwt_token(token)
        
        if not user_id:
            return None
        
        # 获取用户角色
        stmt = select(User).where(User.id == UUID(user_id))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        role = Role(user.role) if user.role in [r.value for r in Role] else Role.USER
        permissions = ROLE_PERMISSIONS.get(role, set())
        
        ip_address = request.client.host if request.client else ""
        
        return SecurityContext(
            user_id=UUID(user_id),
            role=role,
            permissions=permissions,
            ip_address=ip_address,
        )
