"""Commander Real Executor E2E 测试 — 需要真实 Hermes/OpenClaw 后端

默认跳过。运行方式：
  SKIP_REAL_BACKEND=0 COMMANDER_EXECUTOR=real python -m pytest tests/test_commander_real_e2e.py -v
"""
import os
import pytest

# 默认跳过整个模块
pytestmark = [pytest.mark.e2e, pytest.mark.slow]

if os.getenv("SKIP_REAL_BACKEND", "1") != "0":
    pytest.skip(
        "Real backend E2E disabled by default. Set SKIP_REAL_BACKEND=0 to enable.",
        allow_module_level=True,
    )

from commander.models import CommanderSession, CommanderTask, TaskState
from commander.real_executor import RealCommanderExecutor


@pytest.fixture
def session():
    return CommanderSession(user_id="e2e_test", goal="Write a hello world Python script")


@pytest.fixture
def task(session):
    return CommanderTask(
        id="e2e_t1",
        title="Hello World",
        description="Write a Python hello world script",
        state=TaskState.IMPLEMENTING,
    )


@pytest.fixture
def executor():
    return RealCommanderExecutor()


@pytest.mark.asyncio
async def test_real_plan_returns_tasks(executor, session):
    """验证 Hermes 能返回任务列表"""
    result = await executor.plan(session)
    assert "tasks" in result
    assert len(result["tasks"]) >= 1
    task = result["tasks"][0]
    assert "title" in task
    assert "description" in task


@pytest.mark.asyncio
async def test_real_implement_produces_output(executor, session, task):
    """验证 OpenClaw 能产生实现输出"""
    result = await executor.implement(session, task)
    assert result["status"] in ("implemented", "question_pending", "failed")
    if result["status"] == "implemented":
        assert len(result.get("result", "")) > 0


@pytest.mark.asyncio
async def test_real_review_returns_verdict(executor, session, task):
    """验证 Hermes 能返回审查结论"""
    task.result = "print('hello world')"
    result = await executor.review(session, task)
    assert result["status"] in ("approved", "rejected")
    assert "comment" in result


@pytest.mark.asyncio
async def test_real_test_returns_verdict(executor, session, task):
    """验证测试阶段能返回结果"""
    task.result = "print('hello world')"
    result = await executor.test(session, task)
    assert result["status"] in ("passed", "failed")
    assert "output" in result
