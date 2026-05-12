"""Commander Continue 状态推进单元测试 — 验证 10 种状态流转"""
import pytest

pytestmark = pytest.mark.unit

from commander.models import CommanderState, CommanderSession
from commander.service import CommanderService
from commander.fake_executor import FakeCommanderExecutor


@pytest.fixture
def svc():
    return CommanderService(executor=FakeCommanderExecutor())


@pytest.fixture
def session(svc):
    return svc.create_session(user_id="test", goal="Build a REST API")


# ── planning → task_dispatched ─────────────────────────────

@pytest.mark.asyncio
async def test_continue_planning_to_task_dispatched(svc, session):
    result = await svc.continue_session(session.id)
    assert result["state"] == "task_dispatched"
    assert result["event"]["from"] == "planning"
    assert result["event"]["to"] == "task_dispatched"
    assert len(session.tasks) >= 1
    assert session.architect_notes is not None


# ── task_dispatched → implementing ─────────────────────────

@pytest.mark.asyncio
async def test_continue_task_dispatched_to_implementing(svc, session):
    await svc.continue_session(session.id)  # planning → task_dispatched
    assert session.state == CommanderState.TASK_DISPATCHED

    result = await svc.continue_session(session.id)
    assert result["state"] == "implementing"
    assert session.current_task_id is not None


# ── implementing → reviewing ───────────────────────────────

@pytest.mark.asyncio
async def test_continue_implementing_to_reviewing(svc, session):
    await svc.continue_session(session.id)  # planning → task_dispatched
    await svc.continue_session(session.id)  # task_dispatched → implementing
    assert session.state == CommanderState.IMPLEMENTING

    result = await svc.continue_session(session.id)
    assert result["state"] == "reviewing"


# ── implementing → question_pending ────────────────────────

@pytest.mark.asyncio
async def test_continue_implementing_to_question_pending():
    svc = CommanderService(executor=FakeCommanderExecutor(question_pending=True))
    session = svc.create_session(user_id="test", goal="test")
    await svc.continue_session(session.id)  # planning → task_dispatched
    await svc.continue_session(session.id)  # task_dispatched → implementing
    assert session.state == CommanderState.IMPLEMENTING

    result = await svc.continue_session(session.id)
    assert result["state"] == "question_pending"


# ── question_pending → user_decision_required ──────────────

@pytest.mark.asyncio
async def test_continue_question_pending_to_user_decision():
    svc = CommanderService(executor=FakeCommanderExecutor(question_pending=True))
    session = svc.create_session(user_id="test", goal="test")
    await svc.continue_session(session.id)  # planning → task_dispatched
    await svc.continue_session(session.id)  # task_dispatched → implementing
    await svc.continue_session(session.id)  # implementing → question_pending
    assert session.state == CommanderState.QUESTION_PENDING

    result = await svc.continue_session(session.id)
    assert result["state"] == "user_decision_required"


# ── question_pending → implementing (user already answered) ─

@pytest.mark.asyncio
async def test_continue_question_pending_to_implementing_if_answered():
    svc = CommanderService(executor=FakeCommanderExecutor(question_pending=True))
    session = svc.create_session(user_id="test", goal="test")
    await svc.continue_session(session.id)  # planning → task_dispatched
    await svc.continue_session(session.id)  # task_dispatched → implementing
    await svc.continue_session(session.id)  # implementing → question_pending
    # 用户先回答问题
    task = next(t for t in session.tasks if t.id == session.current_task_id)
    task.user_decision = "Use src/ directory"
    assert session.state == CommanderState.QUESTION_PENDING

    result = await svc.continue_session(session.id)
    assert result["state"] == "implementing"


# ── user_decision_required → implementing ──────────────────

@pytest.mark.asyncio
async def test_continue_user_decision_to_implementing():
    svc = CommanderService(executor=FakeCommanderExecutor(question_pending=True))
    session = svc.create_session(user_id="test", goal="test")
    await svc.continue_session(session.id)  # p → td
    await svc.continue_session(session.id)  # td → i
    await svc.continue_session(session.id)  # i → qp
    await svc.continue_session(session.id)  # qp → udr
    assert session.state == CommanderState.USER_DECISION_REQUIRED

    result = await svc.continue_session(session.id)
    assert result["state"] == "implementing"


# ── reviewing → testing (approved) ─────────────────────────

@pytest.mark.asyncio
async def test_continue_reviewing_to_testing(svc, session):
    await svc.continue_session(session.id)  # p → td
    await svc.continue_session(session.id)  # td → i
    await svc.continue_session(session.id)  # i → r
    assert session.state == CommanderState.REVIEWING

    result = await svc.continue_session(session.id)
    assert result["state"] == "testing"


# ── reviewing → rejected ───────────────────────────────────

@pytest.mark.asyncio
async def test_continue_reviewing_to_rejected():
    svc = CommanderService(executor=FakeCommanderExecutor(review_reject=True))
    session = svc.create_session(user_id="test", goal="test")
    await svc.continue_session(session.id)  # p → td
    await svc.continue_session(session.id)  # td → i
    await svc.continue_session(session.id)  # i → r
    assert session.state == CommanderState.REVIEWING

    result = await svc.continue_session(session.id)
    assert result["state"] == "rejected"


# ── testing → accepted ─────────────────────────────────────

@pytest.mark.asyncio
async def test_continue_testing_to_accepted(svc, session):
    await svc.continue_session(session.id)  # p → td
    await svc.continue_session(session.id)  # td → i
    await svc.continue_session(session.id)  # i → r
    await svc.continue_session(session.id)  # r → t
    assert session.state == CommanderState.TESTING

    result = await svc.continue_session(session.id)
    assert result["state"] == "accepted"


# ── testing → rejected (test fail) ─────────────────────────

@pytest.mark.asyncio
async def test_continue_testing_to_rejected():
    svc = CommanderService(executor=FakeCommanderExecutor(test_fail=True))
    session = svc.create_session(user_id="test", goal="test")
    await svc.continue_session(session.id)  # p → td
    await svc.continue_session(session.id)  # td → i
    await svc.continue_session(session.id)  # i → r
    await svc.continue_session(session.id)  # r → t
    assert session.state == CommanderState.TESTING

    result = await svc.continue_session(session.id)
    assert result["state"] == "rejected"


# ── rejected → implementing ────────────────────────────────

@pytest.mark.asyncio
async def test_continue_rejected_to_implementing():
    svc = CommanderService(executor=FakeCommanderExecutor(review_reject=True))
    session = svc.create_session(user_id="test", goal="test")
    await svc.continue_session(session.id)  # p → td
    await svc.continue_session(session.id)  # td → i
    await svc.continue_session(session.id)  # i → reviewing
    await svc.continue_session(session.id)  # reviewing → rejected
    assert session.state == CommanderState.REJECTED

    result = await svc.continue_session(session.id)
    assert result["state"] == "implementing"


# ── edge: terminal state rejection ─────────────────────────

@pytest.mark.asyncio
async def test_continue_from_accepted_raises(svc, session):
    await svc.continue_session(session.id)  # p → td
    await svc.continue_session(session.id)  # td → i
    await svc.continue_session(session.id)  # i → r
    await svc.continue_session(session.id)  # r → t
    await svc.continue_session(session.id)  # t → accepted
    assert session.state == CommanderState.ACCEPTED

    with pytest.raises(ValueError, match="terminal"):
        await svc.continue_session(session.id)


# ── edge: nonexistent session ──────────────────────────────

@pytest.mark.asyncio
async def test_continue_nonexistent_session_raises(svc):
    with pytest.raises(ValueError, match="not found"):
        await svc.continue_session("nonexistent")
