"""初始数据库架构

Revision ID: 001_initial
Revises: 
Create Date: 2026-01-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# 版本标识符
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 用户表
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("contact", sa.String(255), unique=True, nullable=False),
        sa.Column("contact_type", sa.String(20), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("mfa_secret", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_contact", "users", ["contact"])

    # 同意记录表
    op.create_table(
        "consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("health_data_consent", sa.Boolean(), nullable=False, default=False),
        sa.Column("marketing_consent", sa.Boolean(), nullable=False, default=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("consented_at", sa.DateTime(), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=False),
    )
    op.create_index("ix_consents_user_id", "consents", ["user_id"])

    # 健康档案表
    op.create_table(
        "health_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("allergies", postgresql.JSONB(), nullable=True),
        sa.Column("chronic_conditions", postgresql.JSONB(), nullable=True),
        sa.Column("medications", postgresql.JSONB(), nullable=True),
        sa.Column("goals", postgresql.JSONB(), nullable=True),
        sa.Column("dietary_preferences", postgresql.JSONB(), nullable=True),
        sa.Column("budget_min", sa.Numeric(10, 2), nullable=True),
        sa.Column("budget_max", sa.Numeric(10, 2), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_health_profiles_user_id", "health_profiles", ["user_id"])

    # 问卷答案表
    op.create_table(
        "question_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("health_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("health_profiles.id"), nullable=False),
        sa.Column("question_id", sa.String(100), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("answered_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_question_answers_health_profile_id", "question_answers", ["health_profile_id"])

    # 报告上传表
    op.create_table(
        "report_uploads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="UPLOADED"),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("extracted_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_report_uploads_user_id", "report_uploads", ["user_id"])

    # 化验指标表
    op.create_table(
        "lab_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("health_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("health_profiles.id"), nullable=False),
        sa.Column("report_upload_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("report_uploads.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("value", sa.Numeric(10, 4), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("reference_range", sa.String(100), nullable=False),
        sa.Column("flag", sa.String(20), nullable=False),
        sa.Column("extracted_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_lab_metrics_health_profile_id", "lab_metrics", ["health_profile_id"])
    op.create_index("ix_lab_metrics_report_upload_id", "lab_metrics", ["report_upload_id"])

    # 推荐会话表
    op.create_table(
        "recommendation_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("health_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("health_profiles.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="PENDING"),
        sa.Column("requires_review", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_recommendation_sessions_user_id", "recommendation_sessions", ["user_id"])
    op.create_index("ix_recommendation_sessions_health_profile_id", "recommendation_sessions", ["health_profile_id"])

    # 推荐项表
    op.create_table(
        "recommendation_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recommendation_sessions.id"), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("rec_key", sa.String(100), nullable=False),
        sa.Column("name", postgresql.JSONB(), nullable=False),
        sa.Column("why_reasons", postgresql.JSONB(), nullable=False),
        sa.Column("safety_info", postgresql.JSONB(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("commerce_type", sa.String(20), nullable=False),
        sa.Column("commerce_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_recommendation_items_session_id", "recommendation_items", ["session_id"])

    # Shopify 商品表
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shopify_id", sa.String(100), unique=True, nullable=False),
        sa.Column("shopify_variant_id", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, default="TWD"),
        sa.Column("image_url", sa.String(1000), nullable=True),
        sa.Column("in_stock", sa.Boolean(), nullable=False, default=True),
        sa.Column("synced_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_products_shopify_id", "products", ["shopify_id"])
    op.create_index("ix_products_shopify_variant_id", "products", ["shopify_variant_id"])

    # 合作商 Offer 表
    op.create_table(
        "partner_offers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("partner_id", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(1000), nullable=True),
        sa.Column("redirect_url", sa.String(2000), nullable=False),
        sa.Column("payout", sa.Numeric(10, 2), nullable=False),
        sa.Column("cap", sa.Integer(), nullable=True),
        sa.Column("current_clicks", sa.Integer(), nullable=False, default=0),
        sa.Column("active", sa.Boolean(), nullable=False, default=True),
        sa.Column("sponsored", sa.Boolean(), nullable=False, default=True),
    )
    op.create_index("ix_partner_offers_partner_id", "partner_offers", ["partner_id"])

    # 商品映射表
    op.create_table(
        "product_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rec_key", sa.String(100), nullable=False),
        sa.Column("slot_type", sa.String(20), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("offer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("partner_offers.id"), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, default=0),
        sa.Column("active", sa.Boolean(), nullable=False, default=True),
    )
    op.create_index("ix_product_mappings_rec_key", "product_mappings", ["rec_key"])

    # 商品点击追踪表
    op.create_table(
        "commerce_clicks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recommendation_sessions.id"), nullable=False),
        sa.Column("recommendation_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recommendation_items.id"), nullable=False),
        sa.Column("slot_type", sa.String(20), nullable=False),
        sa.Column("commerce_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clicked_at", sa.DateTime(), nullable=False),
        sa.Column("converted", sa.Boolean(), nullable=False, default=False),
    )
    op.create_index("ix_commerce_clicks_user_id", "commerce_clicks", ["user_id"])
    op.create_index("ix_commerce_clicks_session_id", "commerce_clicks", ["session_id"])
    op.create_index("ix_commerce_clicks_recommendation_item_id", "commerce_clicks", ["recommendation_item_id"])

    # 配置版本表
    op.create_table(
        "config_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("config_type", sa.String(50), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="DRAFT"),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("rollout_percent", sa.Integer(), nullable=False, default=0),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=False),
    )
    op.create_index("ix_config_versions_config_type", "config_versions", ["config_type"])

    # 审计日志表
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("config_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("config_versions.id"), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("before_value", postgresql.JSONB(), nullable=True),
        sa.Column("after_value", postgresql.JSONB(), nullable=True),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
    )
    op.create_index("ix_audit_logs_config_version_id", "audit_logs", ["config_version_id"])

    # 审核队列表
    op.create_table(
        "review_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recommendation_sessions.id"), unique=True, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="PENDING"),
        sa.Column("risk_level", sa.String(20), nullable=False, default="MEDIUM"),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
    )
    op.create_index("ix_review_queue_session_id", "review_queue", ["session_id"])

    # 分析事件表
    op.create_table(
        "analytics_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recommendation_sessions.id"), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_data", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
    )
    op.create_index("ix_analytics_events_user_id", "analytics_events", ["user_id"])
    op.create_index("ix_analytics_events_session_id", "analytics_events", ["session_id"])
    op.create_index("ix_analytics_events_event_type", "analytics_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("analytics_events")
    op.drop_table("review_queue")
    op.drop_table("audit_logs")
    op.drop_table("config_versions")
    op.drop_table("commerce_clicks")
    op.drop_table("product_mappings")
    op.drop_table("partner_offers")
    op.drop_table("products")
    op.drop_table("recommendation_items")
    op.drop_table("recommendation_sessions")
    op.drop_table("lab_metrics")
    op.drop_table("report_uploads")
    op.drop_table("question_answers")
    op.drop_table("health_profiles")
    op.drop_table("consents")
    op.drop_table("users")
