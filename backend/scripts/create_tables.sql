-- 智能营养建议平台数据库表结构
-- 在 pgAdmin 的 Query Tool 中执行此脚本

-- 启用 UUID 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contact VARCHAR(255) UNIQUE NOT NULL,
    contact_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP
);
CREATE INDEX ix_users_contact ON users(contact);

-- 同意记录表
CREATE TABLE consents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    health_data_consent BOOLEAN NOT NULL DEFAULT FALSE,
    marketing_consent BOOLEAN NOT NULL DEFAULT FALSE,
    version VARCHAR(50) NOT NULL,
    consented_at TIMESTAMP NOT NULL DEFAULT NOW(),
    ip_address VARCHAR(45) NOT NULL
);
CREATE INDEX ix_consents_user_id ON consents(user_id);

-- 健康档案表
CREATE TABLE health_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    allergies JSONB DEFAULT '[]',
    chronic_conditions JSONB DEFAULT '[]',
    medications JSONB DEFAULT '[]',
    goals JSONB DEFAULT '[]',
    dietary_preferences JSONB DEFAULT '[]',
    budget_min NUMERIC(10, 2),
    budget_max NUMERIC(10, 2),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_health_profiles_user_id ON health_profiles(user_id);

-- 问卷答案表
CREATE TABLE question_answers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    health_profile_id UUID NOT NULL REFERENCES health_profiles(id),
    question_id VARCHAR(100) NOT NULL,
    value JSONB NOT NULL,
    answered_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_question_answers_health_profile_id ON question_answers(health_profile_id);

-- 报告上传表
CREATE TABLE report_uploads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'UPLOADED',
    uploaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    extracted_at TIMESTAMP,
    error_message TEXT
);
CREATE INDEX ix_report_uploads_user_id ON report_uploads(user_id);

-- 化验指标表
CREATE TABLE lab_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    health_profile_id UUID NOT NULL REFERENCES health_profiles(id),
    report_upload_id UUID NOT NULL REFERENCES report_uploads(id),
    name VARCHAR(100) NOT NULL,
    value NUMERIC(10, 4) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    reference_range VARCHAR(100) NOT NULL,
    flag VARCHAR(20) NOT NULL,
    extracted_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_lab_metrics_health_profile_id ON lab_metrics(health_profile_id);
CREATE INDEX ix_lab_metrics_report_upload_id ON lab_metrics(report_upload_id);

-- 推荐会话表
CREATE TABLE recommendation_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    health_profile_id UUID NOT NULL REFERENCES health_profiles(id),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    requires_review BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMP,
    reviewed_by UUID
);
CREATE INDEX ix_recommendation_sessions_user_id ON recommendation_sessions(user_id);
CREATE INDEX ix_recommendation_sessions_health_profile_id ON recommendation_sessions(health_profile_id);

-- 推荐项表
CREATE TABLE recommendation_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES recommendation_sessions(id),
    rank INTEGER NOT NULL,
    rec_key VARCHAR(100) NOT NULL,
    name JSONB NOT NULL,
    why_reasons JSONB NOT NULL,
    safety_info JSONB NOT NULL,
    confidence INTEGER NOT NULL,
    commerce_type VARCHAR(20) NOT NULL,
    commerce_id UUID
);
CREATE INDEX ix_recommendation_items_session_id ON recommendation_items(session_id);

-- Shopify 商品表
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shopify_id VARCHAR(100) UNIQUE NOT NULL,
    shopify_variant_id VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'TWD',
    image_url VARCHAR(1000),
    in_stock BOOLEAN NOT NULL DEFAULT TRUE,
    synced_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_products_shopify_id ON products(shopify_id);
CREATE INDEX ix_products_shopify_variant_id ON products(shopify_variant_id);

-- 合作商 Offer 表
CREATE TABLE partner_offers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    partner_id VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    image_url VARCHAR(1000),
    redirect_url VARCHAR(2000) NOT NULL,
    payout NUMERIC(10, 2) NOT NULL,
    cap INTEGER,
    current_clicks INTEGER NOT NULL DEFAULT 0,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    sponsored BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX ix_partner_offers_partner_id ON partner_offers(partner_id);

-- 商品映射表
CREATE TABLE product_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rec_key VARCHAR(100) NOT NULL,
    slot_type VARCHAR(20) NOT NULL,
    product_id UUID REFERENCES products(id),
    offer_id UUID REFERENCES partner_offers(id),
    priority INTEGER NOT NULL DEFAULT 0,
    active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX ix_product_mappings_rec_key ON product_mappings(rec_key);

-- 商品点击追踪表
CREATE TABLE commerce_clicks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    session_id UUID NOT NULL REFERENCES recommendation_sessions(id),
    recommendation_item_id UUID NOT NULL REFERENCES recommendation_items(id),
    slot_type VARCHAR(20) NOT NULL,
    commerce_id UUID NOT NULL,
    clicked_at TIMESTAMP NOT NULL DEFAULT NOW(),
    converted BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX ix_commerce_clicks_user_id ON commerce_clicks(user_id);
CREATE INDEX ix_commerce_clicks_session_id ON commerce_clicks(session_id);
CREATE INDEX ix_commerce_clicks_recommendation_item_id ON commerce_clicks(recommendation_item_id);

-- 配置版本表
CREATE TABLE config_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_type VARCHAR(50) NOT NULL,
    version INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    content JSONB NOT NULL,
    rollout_percent INTEGER NOT NULL DEFAULT 0,
    created_by UUID NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    change_reason TEXT NOT NULL
);
CREATE INDEX ix_config_versions_config_type ON config_versions(config_type);

-- 审计日志表
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_version_id UUID NOT NULL REFERENCES config_versions(id),
    action VARCHAR(50) NOT NULL,
    before_value JSONB,
    after_value JSONB,
    operator_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    ip_address VARCHAR(45)
);
CREATE INDEX ix_audit_logs_config_version_id ON audit_logs(config_version_id);

-- 审核队列表
CREATE TABLE review_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID UNIQUE NOT NULL REFERENCES recommendation_sessions(id),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    risk_level VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    assigned_to UUID,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP,
    resolution_note TEXT
);
CREATE INDEX ix_review_queue_session_id ON review_queue(session_id);

-- 分析事件表
CREATE TABLE analytics_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    session_id UUID REFERENCES recommendation_sessions(id),
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    ip_address VARCHAR(45),
    user_agent TEXT
);
CREATE INDEX ix_analytics_events_user_id ON analytics_events(user_id);
CREATE INDEX ix_analytics_events_session_id ON analytics_events(session_id);
CREATE INDEX ix_analytics_events_event_type ON analytics_events(event_type);

-- Alembic 版本追踪表（可选，用于后续迁移）
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO alembic_version (version_num) VALUES ('001_initial');
