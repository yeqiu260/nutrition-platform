/**
 * 统一 API 基础 URL 配置
 * 生产环境通过 NEXT_PUBLIC_API_URL 环境变量覆盖
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
