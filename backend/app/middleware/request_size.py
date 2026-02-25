"""请求大小限制中间件 - 防止大文件攻击"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """限制请求体大小"""
    
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 默认 10MB
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 检查 Content-Length
        content_length = request.headers.get("content-length")
        
        if content_length:
            content_length = int(content_length)
            if content_length > self.max_size:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"请求体过大。最大允许: {self.max_size / 1024 / 1024:.1f}MB"
                )
        
        return await call_next(request)
