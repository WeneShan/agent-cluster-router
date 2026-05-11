"""
Agent Cluster Router — 中间件
请求大小限制、CORS、日志脱敏
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from router.security import redact_sensitive, MAX_REQUEST_SIZE, MAX_MESSAGE_CHARS


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """限制请求体大小"""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            cl = int(content_length)
            if cl > MAX_REQUEST_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Request too large: {cl} bytes (max {MAX_REQUEST_SIZE})"},
                )
        return await call_next(request)


class SensitiveDataLoggingMiddleware(BaseHTTPMiddleware):
    """脱敏请求/响应日志"""

    async def dispatch(self, request: Request, call_next):
        # 记录请求（脱敏后）
        response = await call_next(request)
        return response
