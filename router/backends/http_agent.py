
"""HTTP Agent Backend — 通过 HTTP 接入任意第三方 Agent"""
from typing import Any, Dict, List, Optional
from .base import AgentBackend, AgentResponse, HealthStatus


class HttpAgentBackend(AgentBackend):
    """通用 HTTP Agent 后端
    
    任何提供 /chat 和 /health 端点的 HTTP 服务都可以接入。
    通过 config.yaml 配置 url、role、capabilities。
    """

    def __init__(self, name: str, url: str, role: str, capabilities: List[str]):
        import httpx
        self.name = name
        self.url = url.rstrip("/")
        self.role = role
        self.capabilities = capabilities
        self._client = httpx

    async def chat(
        self,
        messages: List[Dict[str, str]],
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        import httpx
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.url}/chat",
                json={
                    "messages": messages,
                    "session_id": session_id,
                    "metadata": metadata or {},
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return AgentResponse(
            content=data.get("content", ""),
            backend=self.name,
            raw=data,
        )

    async def health(self) -> HealthStatus:
        import httpx
        import time
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.url}/health")
            latency = (time.time() - start) * 1000
            return HealthStatus(
                healthy=resp.status_code == 200,
                latency_ms=latency,
            )
        except Exception as e:
            return HealthStatus(healthy=False, reason=str(e))
