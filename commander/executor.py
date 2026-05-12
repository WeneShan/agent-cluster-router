"""
Agent Cluster Router — Commander Executor 抽象
定义所有 Commander 执行器的统一接口，方便接 Fake / 真实 AI 后端
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from commander.models import CommanderSession, CommanderTask


class CommanderExecutor(ABC):
    """Commander 执行器抽象基类

    定义四个核心阶段：
      - plan()    : 目标规划 → 产出任务列表
      - implement(): 任务执行 → 产出代码或结果
      - review()  : 代码审查 → 产出审查结论
      - test()    : 自动测试 → 产出测试结果
    """

    @abstractmethod
    async def plan(
        self, session: CommanderSession
    ) -> Dict[str, Any]:
        """规划阶段：将 session.goal 分解为任务列表

        Returns:
            {
                "tasks": [
                    {"title": "...", "description": "...", "acceptance_criteria": [...]},
                    ...
                ],
                "architect_notes": "..."  # optional
            }
        """
        ...

    @abstractmethod
    async def implement(
        self, session: CommanderSession, task: CommanderTask
    ) -> Dict[str, Any]:
        """实现阶段：执行单个任务

        Returns:
            {
                "status": "implemented" | "question_pending" | "failed",
                "result": "implementation output ...",
                "question": "..."  # only if status == "question_pending"
            }
        """
        ...

    @abstractmethod
    async def review(
        self, session: CommanderSession, task: CommanderTask
    ) -> Dict[str, Any]:
        """审查阶段：审查任务实现

        Returns:
            {
                "status": "approved" | "rejected",
                "comment": "review feedback ..."
            }
        """
        ...

    @abstractmethod
    async def test(
        self, session: CommanderSession, task: CommanderTask
    ) -> Dict[str, Any]:
        """测试阶段：运行自动化测试

        Returns:
            {
                "status": "passed" | "failed",
                "output": "test output ..."
            }
        """
        ...
