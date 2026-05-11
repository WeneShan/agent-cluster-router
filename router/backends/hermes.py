
"""Hermes Backend — 封装 Hermes CLI 为统一 Backend"""
import subprocess
import time
import os
from typing import Any, Dict, List, Optional
from .base import AgentBackend, AgentResponse, HealthStatus, AgentSkill


class HermesBackend(AgentBackend):
    name = "hermes"
    role = "architect"
    capabilities = ["architecture", "planning", "review", "search", "chat"]

    def __init__(self, base_url: str = "http://127.0.0.1:8081"):
        import httpx
        self.base_url = base_url
        self._client = httpx

    async def chat(
        self,
        messages: List[Dict[str, str]],
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """通过 Hermes Adapter HTTP API 调用"""
        import httpx
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                f"{self.base_url}/chat",
                json={
                    "request_id": metadata.get("request_id", "") if metadata else "",
                    "messages": messages,
                    "session_id": session_id or "",
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
        """检查 Hermes 是否可用 — 先测 Hermes CLI，再测 Adapter"""
        start = time.time()
        try:
            # CLI 检查
            result = subprocess.run(
                ["hermes", "--version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                return HealthStatus(healthy=False, reason=f"hermes CLI failed: {result.stderr.strip()}")
        except FileNotFoundError:
            return HealthStatus(healthy=False, reason="hermes CLI not found")
        except Exception as e:
            return HealthStatus(healthy=False, reason=str(e))

        # Adapter HTTP 检查
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/health")
            latency = (time.time() - start) * 1000
            return HealthStatus(
                healthy=resp.status_code == 200,
                latency_ms=latency,
            )
        except Exception as e:
            return HealthStatus(healthy=False, reason=str(e))
