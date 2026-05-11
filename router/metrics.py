"""指标收集器 — 跟踪延迟、请求数、成功率、token 消费"""
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field


@dataclass
class RequestMetric:
    request_id: str
    backend: str
    node: str
    intent: str
    elapsed_ms: float
    success: bool
    tokens_used: int
    timestamp: float = field(default_factory=time.time)


class MetricsCollector:
    def __init__(self, history_size: int = 1000):
        self._lock = threading.Lock()
        # 汇总计数
        self.total_requests: int = 0
        self.success_count: int = 0
        self.error_count: int = 0
        self.total_latency_ms: float = 0.0
        self.total_tokens: int = 0
        # 按后端分组
        self.by_backend: dict[str, dict] = defaultdict(
            lambda: {"requests": 0, "success": 0, "error": 0, "total_latency": 0.0, "total_tokens": 0}
        )
        # 按意图分组
        self.by_intent: dict[str, dict] = defaultdict(
            lambda: {"requests": 0, "success": 0, "error": 0}
        )
        # 延迟历史 (用于 p50/p95/p99)
        self._latency_history: deque[float] = deque(maxlen=history_size)
        # 最近错误
        self._recent_errors: deque[dict] = deque(maxlen=20)
        # 启动时间
        self.start_time: float = time.time()

    def record(self, metric: RequestMetric):
        with self._lock:
            self.total_requests += 1
            if metric.success:
                self.success_count += 1
            else:
                self.error_count += 1

            self.total_latency_ms += metric.elapsed_ms
            self.total_tokens += metric.tokens_used
            self._latency_history.append(metric.elapsed_ms)

            be = self.by_backend[metric.backend]
            be["requests"] += 1
            if metric.success:
                be["success"] += 1
            else:
                be["error"] += 1
            be["total_latency"] += metric.elapsed_ms
            be["total_tokens"] += metric.tokens_used

            bi = self.by_intent[metric.intent]
            bi["requests"] += 1
            if metric.success:
                bi["success"] += 1
            else:
                bi["error"] += 1

            if not metric.success:
                self._recent_errors.append({
                    "request_id": metric.request_id,
                    "backend": metric.backend,
                    "node": metric.node,
                    "elapsed_ms": metric.elapsed_ms,
                    "timestamp": metric.timestamp,
                })

    def snapshot(self) -> dict:
        """返回当前指标快照"""
        with self._lock:
            latencies = sorted(self._latency_history) if self._latency_history else [0]
            n = len(latencies)
            uptime = time.time() - self.start_time

            return {
                "uptime_seconds": round(uptime, 1),
                "summary": {
                    "total_requests": self.total_requests,
                    "success": self.success_count,
                    "error": self.error_count,
                    "success_rate": round(self.success_count / max(self.total_requests, 1), 4),
                    "avg_latency_ms": round(self.total_latency_ms / max(self.total_requests, 1), 1),
                    "total_tokens": self.total_tokens,
                    "requests_per_second": round(self.total_requests / max(uptime, 1), 2),
                },
                "latency_percentiles": {
                    "p50_ms": round(latencies[n // 2], 1),
                    "p95_ms": round(latencies[int(n * 0.95)], 1),
                    "p99_ms": round(latencies[int(n * 0.99)], 1),
                },
                "by_backend": {
                    k: {
                        **v,
                        "avg_latency_ms": round(v["total_latency"] / max(v["requests"], 1), 1),
                        "success_rate": round(v["success"] / max(v["requests"], 1), 4),
                    }
                    for k, v in self.by_backend.items()
                },
                "by_intent": {
                    k: {
                        **v,
                        "success_rate": round(v["success"] / max(v["requests"], 1), 4),
                    }
                    for k, v in self.by_intent.items()
                },
                "recent_errors": list(self._recent_errors)[-10:],
            }

    def reset(self):
        with self._lock:
            self.total_requests = 0
            self.success_count = 0
            self.error_count = 0
            self.total_latency_ms = 0.0
            self.total_tokens = 0
            self.by_backend.clear()
            self.by_intent.clear()
            self._latency_history.clear()
            self._recent_errors.clear()
            self.start_time = time.time()
