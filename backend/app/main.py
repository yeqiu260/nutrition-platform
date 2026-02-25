"""FastAPI 应用入口"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import asyncio

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router  # OTP 登录/注册
# from app.api.questionnaire import router as questionnaire_router  # 旧的问卷系统
# from app.api.recommendation import router as recommendation_router  # 旧的推荐系统
# from app.api.commerce import router as commerce_router  # 旧的商务系统
from app.api.analytics import router as analytics_router  # 分析系统
# from app.api.config import router as config_router  # 配置系统
from app.api.review import router as review_router  # 审核系统
from app.api.quiz import router as quiz_router  # 新的问卷系统
from app.api.debug import router as debug_router
from app.api.admin import router as admin_router
from app.api.report import router as report_router
from app.api.product import router as product_router
from app.api.user_history import router as user_history_router  # 用户历史和收藏
from app.api.affiliate import router as affiliate_router  # Affiliate 追踪
from app.api.postback import router as postback_router  # 转化回调
from app.api.dashboard import router as dashboard_router  # Dashboard
from app.api.mfa import router as mfa_router  # MFA
from app.api.ip_allowlist import router as ip_allowlist_router  # IP 白名单
from app.core.config import get_settings
from app.core.database import close_db
from app.core.redis import close_redis

# DDoS 防护中间件
from app.middleware.rate_limit import RateLimitMiddleware, cleanup_task
from app.middleware.request_size import RequestSizeLimitMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    # 启动时 - 启动清理任务
    cleanup_task_handle = asyncio.create_task(cleanup_task())
    
    yield
    
    # 关闭时
    cleanup_task_handle.cancel()
    await close_db()
    await close_redis()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="智能营养建议平台 API",
    lifespan=lifespan,
)

# ============ DDoS 防护中间件（按顺序添加）============

# 1. 请求大小限制（最先检查，防止大文件攻击）
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_size=10 * 1024 * 1024  # 10MB
)

# 2. 全局速率限制（防止暴力请求）
app.add_middleware(
    RateLimitMiddleware,
    max_requests=100,  # 每分钟最多 100 个请求
    window=60  # 60秒窗口
)

# 3. CORS 中间件（必须在最外层）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 全局异常处理器 - 确保 CORS 头被添加
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理，确保返回正确的 CORS 头"""
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

# 注意：暂时禁用这些中间件，因为它们可能导致问题
# app.add_middleware(ConsentCheckMiddleware)
# app.add_middleware(RBACMiddleware)

# 注册路由
app.include_router(auth_router)
# app.include_router(questionnaire_router)  # 暂时注释，依赖旧模型
# app.include_router(recommendation_router)  # 暂时注释，依赖旧模型
# app.include_router(commerce_router)  # 暂时注释
app.include_router(analytics_router)  # 分析事件追踪 API
# app.include_router(config_router)  # 暂时注释
app.include_router(review_router)  # 审核系统
app.include_router(quiz_router)  # 新的问卷 API
# app.include_router(debug_router)  # 暂时注释
app.include_router(admin_router)  # 管理员 API
app.include_router(report_router)  # 报告上传和抽取 API
app.include_router(product_router)  # 商品 API
app.include_router(user_history_router)  # 用户历史和收藏 API
app.include_router(affiliate_router)  # Affiliate 追踪 API
app.include_router(postback_router)  # 转化回调 API
app.include_router(dashboard_router)  # Dashboard API
app.include_router(mfa_router)  # MFA API
app.include_router(ip_allowlist_router)  # IP 白名单 API


@app.get("/health")
async def health_check() -> dict:
    """健康检查端点"""
    return {"status": "healthy", "version": settings.app_version}


@app.get("/")
async def root() -> dict:
    """根端点"""
    return {"message": "欢迎使用智能营养建议平台 API", "docs": "/docs"}
