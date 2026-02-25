"""应用配置"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv


# 获取 .env 文件路径并加载
# __file__ is in backend/app/core/config.py
# We need to go up 3 levels to get to backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"

# 显式加载 .env 文件
load_dotenv(ENV_FILE)


class Settings(BaseSettings):
    """应用配置类"""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用配置
    app_name: str = "智能营养建议平台"
    app_version: str = "0.1.0"
    debug: bool = False
    secret_key: str = "change-me-in-production"

    # 数据库配置
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/nutrition_db"

    # Redis 配置
    redis_url: str = "redis://localhost:6379/0"

    # Celery 配置
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # JWT 配置
    jwt_secret_key: str = "jwt-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24小时

    # OTP 配置
    otp_expire_minutes: int = 10
    otp_max_attempts: int = 5

    # S3/R2 配置
    s3_endpoint_url: Optional[str] = None
    s3_access_key_id: Optional[str] = None
    s3_secret_access_key: Optional[str] = None
    s3_bucket_name: str = "nutrition-reports"
    s3_region: str = "auto"

    # Grok AI 配置
    grok_api_key: str = os.getenv("GROK_API_KEY", "")

    # 邮件配置
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    smtp_from_name: str = "WysikHealth"

    # Shopify 配置
    shopify_shop_domain: Optional[str] = None
    shopify_access_token: Optional[str] = None
    shopify_api_version: str = "2024-01"

    # 静态加密配置
    encryption_key: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


def clear_settings_cache():
    """清除设置缓存"""
    get_settings.cache_clear()
