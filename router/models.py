"""内部标准请求模型 — Router 与后端之间的统一协议"""
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional
import json
import uuid


class TaskIntent(str, Enum):
    CHAT = "chat"
    TOOL = "tool"
    SEARCH = "search"
    PLAN = "plan"
    CODE = "code"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class RouteStrategy(str, Enum):
    AUTO = "auto"
    OPENCLAW = "openclaw"
    HERMES = "hermes"


@dataclass
class Message:
    role: str  # system | user | assistant
    content: str

    def to_dict(self):
        return {"role": self.role, "content": self.content}


@dataclass
class TaskDefinition:
    intent: TaskIntent = TaskIntent.CHAT
    priority: Priority = Priority.NORMAL
    tags: list[str] = field(default_factory=list)


@dataclass
class InputContext:
    messages: list[Message] = field(default_factory=list)
    memory_namespace: Optional[str] = None
    tool_allowlist: list[str] = field(default_factory=list)


@dataclass
class RoutingHint:
    preferred: RouteStrategy = RouteStrategy.AUTO
    canary_ratio: float = 0.0  # 发往 hermes 的比例


@dataclass
class RuntimeParams:
    timeout_ms: int = 60000
    max_steps: int = 20


@dataclass
class AgentRequest:
    """Router → Backend 内部请求 (归一化格式)"""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task: TaskDefinition = field(default_factory=TaskDefinition)
    input: InputContext = field(default_factory=InputContext)
    routing: RoutingHint = field(default_factory=RoutingHint)
    runtime: RuntimeParams = field(default_factory=RuntimeParams)

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "task": {
                "intent": self.task.intent.value,
                "priority": self.task.priority.value,
                "tags": self.task.tags,
            },
            "input": {
                "messages": [m.to_dict() for m in self.input.messages],
                "memory_namespace": self.input.memory_namespace,
                "tool_allowlist": self.input.tool_allowlist,
            },
            "routing": {
                "preferred": self.routing.preferred.value,
                "canary_ratio": self.routing.canary_ratio,
            },
            "runtime": {
                "timeout_ms": self.runtime.timeout_ms,
                "max_steps": self.runtime.max_steps,
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class AgentResponse:
    """Backend → Router 统一响应"""
    request_id: str
    backend: str  # "openclaw" | "hermes"
    node_name: str
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    tokens_used: int = 0
    elapsed_ms: float = 0.0
    error: Optional[str] = None
    success: bool = True

    def to_dict(self) -> dict:
        return asdict(self)
