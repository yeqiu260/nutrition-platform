"""速率限制中间件 - 防止 DDoS 攻击"""

import time
from collections import defaultdict
from typing import Callable, Dict, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import asyncio


class RateLimiter:
    """基于内存的速率限制器"""
    
    def __init__(self):
        # IP -> (请求次数, 窗口开始时间)
        self.requests: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, time.time()))
        # IP -> 封禁到期时间
        self.blocked: Dict[str, float] = {}
        self.lock = asyncio.Lock()
    
    async def is_allowed(
        self, 
        ip: str, 
        max_requests: int = 100, 
        window: int = 60,
        block_duration: int = 300
    ) -> Tuple[bool, int]:
        """
        检查 IP 是否允许请求
        
        Args:
            ip: 客户端 IP
            max_requests: 时间窗口内最大请求数
            window: 时间窗口（秒）
            block_duration: 封禁时长（秒）
        
        Returns:
            (是否允许, 剩余请求数)
        """
        async with self.lock:
            current_time = time.time()
            
            # 检查是否被封禁
            if ip in self.blocked:
                if current_time < self.blocked[ip]:
                    return False, 0
                else:
                    # 解除封禁
                    del self.blocked[ip]
            
            # 获取请求记录
            count, start_time = self.requests[ip]
            
            # 检查是否需要重置窗口
            if current_time - start_time > window:
                self.requests[ip] = (1, current_time)
                return True, max_requests - 1
            
            # 检查是否超过限制
            if count >= max_requests:
                # 封禁 IP
                self.blocked[ip] = current_time + block_duration
                return False, 0
            
            # 增加计数
            self.requests[ip] = (count + 1, start_time)
            return True, max_requests - count - 1
    
    async def cleanup(self):
        """清理过期数据"""
        async with self.lock:
            current_time = time.time()
            
            # 清理过期的请求记录
            expired_ips = [
                ip for ip, (_, start_time) in self.requests.items()
                if current_time - start_time > 3600  # 1小时后清理
            ]
            for ip in expired_ips:
                del self.requests[ip]
            
            # 清理过期的封禁记录
            expired_blocks = [
                ip for ip, expire_time in self.blocked.items()
                if current_time > expire_time
            ]
            for ip in expired_blocks:
                del self.blocked[ip]


# 全局限流器实例
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件"""
    
    def __init__(self, app, max_requests: int = 100, window: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 获取客户端 IP
        client_ip = request.client.host if request.client else "unknown"
        
        # 从 X-Forwarded-For 获取真实 IP（如果使用代理）
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        
        # 检查速率限制
        allowed, remaining = await rate_limiter.is_allowed(
            client_ip, 
            self.max_requests, 
            self.window
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"请求过于频繁，请稍后再试。IP: {client_ip} 已被临时封禁。"
            )
        
        # 添加速率限制响应头
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + self.window))
        
        return response


# 定期清理任务
async def cleanup_task():
    """定期清理过期数据"""
    while True:
        await asyncio.sleep(300)  # 每5分钟清理一次
        await rate_limiter.cleanup()
