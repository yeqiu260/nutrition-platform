/**
 * 统一 API 基础 URL 配置
 * 生产环境通过 NEXT_PUBLIC_API_URL 环境变量覆盖
 */
export const API_BASE_URL = typeof window !== 'undefined'
    ? '' // 浏览器端：使用相对路径，由 Next.js rewrites 代理
    : (process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000'); // 服务端 SSR：直接请求内部 Docker 容器
