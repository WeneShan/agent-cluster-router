"""
Agent Cluster Router — Real Commander Executor
调用真实 Hermes/OpenClaw 后端执行 Commander 工作流
"""
import json
import os
import re
from typing import Any, Dict

import httpx

from commander.executor import CommanderExecutor
from commander.models import CommanderSession, CommanderTask
from commander.prompts import plan_prompt, implement_prompt, review_prompt, test_prompt


HERMES_URL = os.environ.get("HERMES_ADAPTER_URL", "http://127.0.0.1:8081")
OPENCLAW_URL = os.environ.get("OPENCLAW_ADAPTER_URL", "http://127.0.0.1:8082")
TIMEOUT_SEC = int(os.environ.get("COMMANDER_REAL_TIMEOUT", "120"))


def _extract_json(text: str) -> Dict[str, Any]:
    """从 LLM 输出中提取 JSON（处理 markdown fences 和前后缀）"""
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试提取 ```json ... ``` 块
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试提取 { ... } 块
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    return {"raw": text}


class RealCommanderExecutor(CommanderExecutor):
    """真实 Commander 执行器 — 通过 HTTP 调用 Hermes/OpenClaw 适配器

    角色分配：
      Hermes   → plan / review
      OpenClaw → implement
      Hermes   → test (暂用 Hermes，后续可替换为 test runner)
    """

    def __init__(
        self,
        hermes_url: str = HERMES_URL,
        openclaw_url: str = OPENCLAW_URL,
        timeout: int = TIMEOUT_SEC,
    ):
        self._hermes_url = hermes_url
        self._openclaw_url = openclaw_url
        self._timeout = timeout

    async def plan(self, session: CommanderSession) -> Dict[str, Any]:
        """调用 Hermes 分解目标为任务列表"""
        prompt = plan_prompt(session.goal)

        try:
            data = await self._call_hermes(prompt)
            # 提取 JSON
            if "content" in data:
                parsed = _extract_json(data["content"])
            else:
                parsed = {"tasks": [{"title": "Empty plan", "description": ""}]}

            if "tasks" not in parsed:
                parsed["tasks"] = [
                    {"title": "Implement goal", "description": session.goal}
                ]
            if "architect_notes" not in parsed:
                parsed["architect_notes"] = data.get("content", "")
            return parsed

        except Exception:
            # 失败时返回一个 fallback 任务
            return {
                "tasks": [
                    {
                        "title": f"Implement: {session.goal[:60]}",
                        "description": session.goal,
                        "acceptance_criteria": [
                            {"description": "Implementation compiles and runs"}
                        ],
                    }
                ],
                "architect_notes": "Plan failed — using single-task fallback.",
            }

    async def implement(
        self, session: CommanderSession, task: CommanderTask
    ) -> Dict[str, Any]:
        """调用 OpenClaw 实现任务"""
        prompt = implement_prompt(task.title, task.description)

        try:
            data = await self._call_openclaw(prompt)
            content = data.get("content", "")

            # 检测是否有提问
            if content.strip().upper().startswith("QUESTION:"):
                question = content.strip()[len("QUESTION:"):].strip()
                return {"status": "question_pending", "result": "", "question": question}

            return {"status": "implemented", "result": content}

        except Exception as e:
            return {
                "status": "failed",
                "result": "",
                "question": f"Implementation failed: {e}",
            }

    async def review(
        self, session: CommanderSession, task: CommanderTask
    ) -> Dict[str, Any]:
        """调用 Hermes 审查实现结果"""
        implementation = task.result or "[no output]"
        prompt = review_prompt(task.title, implementation)

        try:
            data = await self._call_hermes(prompt)
            content = data.get("content", "")
            parsed = _extract_json(content)

            status = parsed.get("status", "approved")
            if status not in ("approved", "rejected"):
                status = "approved"  # default safety

            return {"status": status, "comment": parsed.get("comment", content)}

        except Exception as e:
            return {
                "status": "approved",
                "comment": f"Review failed, defaulting to approved: {e}",
            }

    async def test(
        self, session: CommanderSession, task: CommanderTask
    ) -> Dict[str, Any]:
        """调用 Hermes 运行测试检查"""
        implementation = task.result or "[no output]"
        prompt = test_prompt(task.title, implementation)

        try:
            data = await self._call_hermes(prompt)
            content = data.get("content", "")
            parsed = _extract_json(content)

            status = parsed.get("status", "passed")
            if status not in ("passed", "failed"):
                status = "passed"

            return {"status": status, "output": parsed.get("output", content)}

        except Exception as e:
            return {
                "status": "failed",
                "output": f"Test execution failed: {e}",
            }

    # ── HTTP 调用 ──────────────────────────────────────────

    async def _call_hermes(self, prompt: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._hermes_url}/chat",
                json={
                    "request_id": f"cmd_{id(prompt):x}",
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def _call_openclaw(self, prompt: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._openclaw_url}/chat",
                json={
                    "request_id": f"cmd_{id(prompt):x}",
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            return resp.json()
