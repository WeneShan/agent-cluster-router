"""
Agent Cluster Router — 错误处理模块
统一错误响应格式和超时/重试/熔断框架
"""
import time
import asyncio
from typing import Callable, Awaitable, Any


# --- 统一错误响应 ---
class RouterError(Exception):
    """Router 基础异常"""
    def __init__(self, message: str, status_code: int = 500, detail: dict = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}


class BackendUnreachableError(RouterError):
    """后端不可达"""
    def __init__(self, backend: str, reason: str = ""):
        super().__init__(
            message=f"Backend '{backend}' unreachable",
            status_code=502,
            detail={"backend": backend, "reason": reason},
        )


class TimeoutError(RouterError):
    """请求超时"""
    def __init__(self, backend: str, timeout_s: float):
        super().__init__(
            message=f"Backend '{backend}' timed out after {timeout_s}s",
            status_code=504,
            detail={"backend": backend, "timeout_seconds": timeout_s},
        )


class RateLimitError(RouterError):
    """限流"""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Rate limit exceeded",
            status_code=429,
            detail={"retry_after": retry_after},
        )


# --- 重试 ---
async def with_retry(
    fn: Callable[[], Awaitable[Any]],
    max_retries: int = 2,
    delay_seconds: float = 1.0,
    backoff_multiplier: float = 2.0,
) -> Any:
    """带指数退避的重试
    
    Args:
        fn: 异步函数
        max_retries: 最大重试次数
        delay_seconds: 初始延迟
        backoff_multiplier: 退避系数
    """
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return await fn()
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                wait = delay_seconds * (backoff_multiplier ** attempt)
                await asyncio.sleep(wait)
    raise last_error


# --- 熔断器 ---
class CircuitBreaker:
    """简单熔断器
    
    连续失败达到阈值后打开，一段时间后进入半开状态。
    """

    def __init__(self, failure_threshold: int = 5, recovery_seconds: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self._failures = 0
        self._open_until = 0.0

    @property
    def is_open(self) -> bool:
        """熔断器是否处于开启状态"""
        return time.time() < self._open_until

    def allow(self) -> bool:
        """是否允许请求通过"""
        return not self.is_open

    def record_success(self):
        """记录成功 — 重置熔断器"""
        self._failures = 0
        self._open_until = 0.0

    def record_failure(self):
        """记录失败 — 可能触发熔断"""
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._open_until = time.time() + self.recovery_seconds

    def status(self) -> dict:
        """获取当前状态"""
        return {
            "state": "open" if self.is_open else "closed",
            "failures": self._failures,
            "threshold": self.failure_threshold,
            "recovery_in": max(0, self._open_until - time.time()) if self.is_open else 0,
        }
