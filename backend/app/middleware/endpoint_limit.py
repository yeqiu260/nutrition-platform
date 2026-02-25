"""API 端点特定限流装饰器"""

from functools import wraps
from fastapi import Request, HTTPException, status
from typing import Callable
import time
from collections import defaultdict
import asyncio


class EndpointRateLimiter:
    """端点级别的速率限制器"""
    
    def __init__(self):
        # (IP, endpoint) -> (请求次数, 窗口开始时间)
        self.requests = defaultdict(lambda: (0, time.time()))
        self.lock = asyncio.Lock()
    
    async def check_limit(
        self, 
        ip: str, 
        endpoint: str, 
        max_requests: int, 
        window: int
    ) -> bool:
        """检查端点限流"""
        async with self.lock:
            key = f"{ip}:{endpoint}"
            current_time = time.time()
            count, start_time = self.requests[key]
            
            # 重置窗口
            if current_time - start_time > window:
                self.requests[key] = (1, current_time)
                return True
            
            # 检查限制
            if count >= max_requests:
                return False
            
            # 增加计数
            self.requests[key] = (count + 1, start_time)
            return True


endpoint_limiter = EndpointRateLimiter()


def rate_limit(max_requests: int = 10, window: int = 60):
    """
    端点限流装饰器
    
    Args:
        max_requests: 时间窗口内最大请求数
        window: 时间窗口（秒）
    
    Example:
        @router.post("/expensive-operation")
        @rate_limit(max_requests=5, window=60)
        async def expensive_operation():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从参数中获取 request
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                request = kwargs.get('request')
            
            if request:
                client_ip = request.client.host if request.client else "unknown"
                forwarded = request.headers.get("X-Forwarded-For")
                if forwarded:
                    client_ip = forwarded.split(",")[0].strip()
                
                endpoint = request.url.path
                
                allowed = await endpoint_limiter.check_limit(
                    client_ip, 
                    endpoint, 
                    max_requests, 
                    window
                )
                
                if not allowed:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"此操作请求过于频繁，请 {window} 秒后再试"
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
