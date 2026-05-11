"""
Agent Cluster Router — 统一 Agent Backend 抽象接口
所有 Agent 后端必须实现此接口
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class AgentSkill(BaseModel):
    """Agent 拥有的技能"""
    name: str
    description: str = ""
    aliases: List[str] = []


class AgentResponse(BaseModel):
    """Agent 返回的统一响应"""
    content: str
    backend: str
    raw: Optional[Dict[str, Any]] = None


class HealthStatus(BaseModel):
    """Agent 健康状态"""
    healthy: bool
    reason: Optional[str] = None
    latency_ms: Optional[float] = None


class AgentBackend(ABC):
    """Agent 后端抽象基类
    
    所有后端实现必须提供 name、role、capabilities 类属性，
    并实现 chat() 和 health() 方法。
    """
    name: str
    role: str
    capabilities: List[str]

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """发送消息给 Agent 并获取回复"""
        ...

    @abstractmethod
    async def health(self) -> HealthStatus:
        """检查 Agent 是否可用"""
        ...

    async def list_skills(self) -> List[AgentSkill]:
        """返回 Agent 拥有的技能列表"""
        return []

    async def supports_intent(self, intent: str) -> bool:
        """检查 Agent 是否支持某个意图"""
        return intent in self.capabilities
