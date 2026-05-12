"""
Agent Cluster Router — 限流模块
基于内存的简单限流器（支持 IP + API Key 组合限流）
"""
import time
from collections import defaultdict, deque
from fastapi import HTTPException, Request


class InMemoryRateLimiter:
    """内存限流器 — 滑动窗口算法"""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque] = defaultdict(deque)

    def check(self, key: str) -> None:
        """检查 key 是否超过限流阈值"""
        now = time.time()
        q = self._requests[key]

        # 清理过期请求
        while q and now - q[0] > self.window_seconds:
            q.popleft()

        # 检查限流
        if len(q) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - q[0]))
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Retry after {retry_after}s",
                headers={"Retry-After": str(retry_after)},
            )

        q.append(now)

    def get_usage(self, key: str) -> dict:
        """获取当前使用情况"""
        now = time.time()
        q = self._requests[key]
        while q and now - q[0] > self.window_seconds:
            q.popleft()
        return {
            "current": len(q),
            "limit": self.max_requests,
            "window_seconds": self.window_seconds,
            "remaining": max(0, self.max_requests - len(q)),
        }

    def reset(self, key: str = None):
        """重置限流状态"""
        if key:
            self._requests.pop(key, None)
        else:
            self._requests.clear()


# 全局单例 — dry_run 不消耗配额
import os

_max = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "60"))
_win = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
_limiter = InMemoryRateLimiter(max_requests=_max, window_seconds=_win)


async def rate_limit(request: Request):
    """FastAPI Depends — 对每个请求进行限流
    
    限流 key = API_Key:Client_IP
    """
    api_key = request.headers.get("x-api-key", "anonymous")
    client_ip = request.client.host if request.client else "unknown"
    key = f"{api_key}:{client_ip}"
    _limiter.check(key)
    return True
