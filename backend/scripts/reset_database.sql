-- 重置数据库脚本
-- 警告：这将删除所有数据！

-- 删除所有表（CASCADE 会自动删除依赖的外键）
DROP TABLE IF EXISTS commerce_clicks CASCADE;
DROP TABLE IF EXISTS recommendation_items CASCADE;
DROP TABLE IF EXISTS recommendation_sessions CASCADE;
DROP TABLE IF EXISTS partner_offers CASCADE;
DROP TABLE IF EXISTS product_mappings CASCADE;
DROP TABLE IF EXISTS analytics_events CASCADE;
DROP TABLE IF EXISTS config_versions CASCADE;
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS review_queue CASCADE;
DROP TABLE IF EXISTS question_answers CASCADE;
DROP TABLE IF EXISTS consents CASCADE;
DROP TABLE IF EXISTS health_profiles CASCADE;
DROP TABLE IF EXISTS lab_metrics CASCADE;
DROP TABLE IF EXISTS report_uploads CASCADE;

-- 删除 alembic 版本表（重新开始迁移）
DROP TABLE IF EXISTS alembic_version CASCADE;

-- 现有的表保留
-- users, admin_users, system_configs, products, ai_usage, partners, quiz_questions, supplements
