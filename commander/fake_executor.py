"""
Agent Cluster Router — Fake Commander Executor
测试用假执行器，不依赖真实 AI 后端，返回可配置的模拟结果
"""
from typing import Any, Dict, Optional

from commander.executor import CommanderExecutor
from commander.models import CommanderSession, CommanderTask


class FakeCommanderExecutor(CommanderExecutor):
    """假执行器 — 所有阶段返回预设的模拟结果

    支持可配置行为，方便测试不同分支：
      - question_pending : 强制 implement 阶段"提问"
      - review_reject    : 强制 review 阶段"驳回"
      - test_fail        : 强制 test 阶段"失败"
    """

    def __init__(
        self,
        question_pending: bool = False,
        review_reject: bool = False,
        test_fail: bool = False,
    ):
        self._question_pending = question_pending
        self._review_reject = review_reject
        self._test_fail = test_fail

    async def plan(self, session: CommanderSession) -> Dict[str, Any]:
        """返回一个假任务列表"""
        return {
            "tasks": [
                {
                    "title": f"Implement: {session.goal[:60]}",
                    "description": (
                        f"Create a minimal implementation for: {session.goal}"
                    ),
                    "acceptance_criteria": [
                        {"description": "Code compiles / runs without error"},
                        {"description": "Basic functionality verified"},
                    ],
                }
            ],
            "architect_notes": (
                "Fake plan — single task, no AI backend involved. "
                "Use a simple function-based approach with tests."
            ),
        }

    async def implement(
        self, session: CommanderSession, task: CommanderTask
    ) -> Dict[str, Any]:
        """模拟实现任务"""
        if self._question_pending:
            return {
                "status": "question_pending",
                "result": "",
                "question": (
                    "Fake question: which directory should the implementation "
                    "files be placed in — 'src/' or 'lib/'?"
                ),
            }

        return {
            "status": "implemented",
            "result": (
                f"[Fake] Implementation complete for task '{task.title}'. "
                f"Created placeholder artifacts — no real code was generated."
            ),
        }

    async def review(
        self, session: CommanderSession, task: CommanderTask
    ) -> Dict[str, Any]:
        """模拟审查"""
        if self._review_reject:
            return {
                "status": "rejected",
                "comment": "Fake review rejected — needs better error handling.",
            }

        return {
            "status": "approved",
            "comment": "Fake review passed — code looks good.",
        }

    async def test(
        self, session: CommanderSession, task: CommanderTask
    ) -> Dict[str, Any]:
        """模拟自动化测试"""
        if self._test_fail:
            return {
                "status": "failed",
                "output": "Fake test failed — assertion error on line 42.",
            }

        return {
            "status": "passed",
            "output": "Fake tests passed — 3/3 assertions OK.",
        }
