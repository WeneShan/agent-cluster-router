
"""OpenClaw Backend — 封装 OpenClaw CLI 为统一 Backend"""
import subprocess
import time
import os
from typing import Any, Dict, List, Optional
from .base import AgentBackend, AgentResponse, HealthStatus, AgentSkill


class OpenClawBackend(AgentBackend):
    name = "openclaw"
    role = "engineer"
    capabilities = ["code", "debug", "refactor", "tool_use"]

    # 已注册的 skills
    _SKILLS = [
        AgentSkill(name="github", aliases=["仓库", "GitHub", "repo"], description="GitHub 仓库操作"),
        AgentSkill(name="weather", aliases=["天气", "气温"], description="天气查询"),
        AgentSkill(name="email", aliases=["邮件", "发邮件"], description="邮件发送"),
        AgentSkill(name="notion", aliases=["Notion", "笔记"], description="Notion 操作"),
        AgentSkill(name="web_search", aliases=["搜索", "查资料"], description="网页搜索"),
    ]

    def __init__(self, base_url: str = "http://127.0.0.1:8082"):
        import httpx
        self.base_url = base_url
        self._client = httpx

    async def chat(
        self,
        messages: List[Dict[str, str]],
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """通过 OpenClaw Adapter HTTP API 调用"""
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
        """检查 OpenClaw 是否可用"""
        start = time.time()
        try:
            result = subprocess.run(
                ["openclaw", "--version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                return HealthStatus(healthy=False, reason=f"openclaw CLI failed: {result.stderr.strip()}")
        except FileNotFoundError:
            return HealthStatus(healthy=False, reason="openclaw CLI not found")
        except Exception as e:
            return HealthStatus(healthy=False, reason=str(e))

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

    async def list_skills(self) -> List[AgentSkill]:
        return self._SKILLS
