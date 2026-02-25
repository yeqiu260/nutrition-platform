"""Celery 配置"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "nutrition_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery 配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5分钟超时
    task_soft_time_limit=240,  # 4分钟软超时
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# 自动发现任务
celery_app.autodiscover_tasks(["app.tasks"])
