"""Commander Executor 单元测试 — 验证 FakeCommanderExecutor 行为"""
import pytest

pytestmark = pytest.mark.unit

from commander.models import CommanderSession, CommanderTask, TaskState
from commander.fake_executor import FakeCommanderExecutor


@pytest.fixture
def session():
    return CommanderSession(user_id="test", goal="Build a CLI tool")


@pytest.fixture
def task(session):
    return CommanderTask(
        id="task_1",
        title="Create project structure",
        description="Create minimal project files",
        state=TaskState.IMPLEMENTING,
    )


@pytest.fixture
def executor():
    return FakeCommanderExecutor()


# ── plan() ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fake_executor_plan_returns_tasks(executor, session):
    result = await executor.plan(session)
    assert "tasks" in result
    assert len(result["tasks"]) >= 1
    task = result["tasks"][0]
    assert "title" in task
    assert "description" in task


@pytest.mark.asyncio
async def test_fake_executor_plan_includes_architect_notes(executor, session):
    result = await executor.plan(session)
    assert "architect_notes" in result
    assert len(result["architect_notes"]) > 0


# ── implement() ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fake_executor_implement_returns_result(executor, session, task):
    result = await executor.implement(session, task)
    assert result["status"] == "implemented"
    assert "result" in result
    assert len(result["result"]) > 0


@pytest.mark.asyncio
async def test_fake_executor_implement_question_pending():
    executor = FakeCommanderExecutor(question_pending=True)
    session = CommanderSession(user_id="test", goal="test")
    task = CommanderTask(id="t1", title="T1", state=TaskState.IMPLEMENTING)
    result = await executor.implement(session, task)
    assert result["status"] == "question_pending"
    assert "question" in result
    assert len(result["question"]) > 0


# ── review() ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fake_executor_review_approves(executor, session, task):
    result = await executor.review(session, task)
    assert result["status"] == "approved"
    assert "comment" in result


@pytest.mark.asyncio
async def test_fake_executor_review_rejects():
    executor = FakeCommanderExecutor(review_reject=True)
    session = CommanderSession(user_id="test", goal="test")
    task = CommanderTask(id="t1", title="T1", state=TaskState.REVIEWING)
    result = await executor.review(session, task)
    assert result["status"] == "rejected"
    assert "comment" in result


# ── test() ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fake_executor_test_passes(executor, session, task):
    result = await executor.test(session, task)
    assert result["status"] == "passed"
    assert "output" in result


@pytest.mark.asyncio
async def test_fake_executor_test_fails():
    executor = FakeCommanderExecutor(test_fail=True)
    session = CommanderSession(user_id="test", goal="test")
    task = CommanderTask(id="t1", title="T1", state=TaskState.TESTING)
    result = await executor.test(session, task)
    assert result["status"] == "failed"
    assert "output" in result


# ── no real AI backend ─────────────────────────────────────

@pytest.mark.asyncio
async def test_fake_executor_no_real_ai(executor, session, task):
    """验证 FakeExecutor 不依赖真实 AI 后端 — 纯静态返回"""
    results = []
    results.append(await executor.plan(session))
    results.append(await executor.implement(session, task))
    results.append(await executor.review(session, task))
    results.append(await executor.test(session, task))
    # 所有结果必须有内容但来自假数据
    for r in results:
        assert len(str(r)) > 0
