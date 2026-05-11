
"""CLI Agent Backend — 通过命令行调用任意 AI CLI 工具"""
import subprocess
import time
from typing import Any, Dict, List, Optional
from .base import AgentBackend, AgentResponse, HealthStatus


class CliAgentBackend(AgentBackend):
    """通用 CLI Agent 后端
    
    通过 shell 命令调用任意 CLI AI 工具（如 aider、codex 等）。
    配置示例：command="aider --model gpt-4o --no-git"
    """

    def __init__(self, name: str, command: str, role: str, capabilities: List[str],
                 timeout_seconds: int = 120, working_dir: str = "."):
        self.name = name
        self.command = command  # 完整命令，如 "aider --model gpt-4o --message"
        self.role = role
        self.capabilities = capabilities
        self.timeout_seconds = timeout_seconds
        self.working_dir = working_dir

    async def chat(
        self,
        messages: List[Dict[str, str]],
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """通过 CLI 命令调用 Agent"""
        # 拼接用户消息为 prompt
        user_messages = [m["content"] for m in messages if m.get("role") == "user"]
        prompt = "\n".join(user_messages)

        cmd = self.command.split() + [prompt]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                cwd=self.working_dir,
            )
            content = result.stdout.strip()
            if result.returncode != 0 and not content:
                content = f"[error] {result.stderr.strip()}"
        except subprocess.TimeoutExpired:
            content = "[error] CLI agent timed out"
        except Exception as e:
            content = f"[error] {str(e)}"

        return AgentResponse(
            content=content,
            backend=self.name,
        )

    async def health(self) -> HealthStatus:
        """检查 CLI Agent 是否可用 — 试运行 --version"""
        start = time.time()
        try:
            # 取命令的第一部分作为可执行文件名
            executable = self.command.split()[0]
            result = subprocess.run(
                [executable, "--version"],
                capture_output=True, text=True, timeout=10
            )
            latency = (time.time() - start) * 1000
            return HealthStatus(
                healthy=result.returncode == 0,
                latency_ms=latency,
            )
        except FileNotFoundError:
            return HealthStatus(healthy=False, reason=f"{executable} not found")
        except Exception as e:
            return HealthStatus(healthy=False, reason=str(e))
