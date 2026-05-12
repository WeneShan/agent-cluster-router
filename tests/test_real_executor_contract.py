"""RealCommanderExecutor 契约测试 — 验证接口实现和参数传递"""
import pytest
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.unit

from commander.models import CommanderSession, CommanderTask, TaskState
from commander.real_executor import RealCommanderExecutor, _extract_json


@pytest.fixture
def session():
    return CommanderSession(user_id="test", goal="Build a REST API")


@pytest.fixture
def task(session):
    return CommanderTask(
        id="t1",
        title="Create project structure",
        description="Create minimal project files",
        state=TaskState.IMPLEMENTING,
        result="fake implementation",
    )


# ── _extract_json ──────────────────────────────────────────

def test_extract_json_valid():
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_with_markdown_fence():
    result = _extract_json('```json\n{"b": 2}\n```')
    assert result == {"b": 2}


def test_extract_json_with_prefix_suffix():
    result = _extract_json('Some text {"c": 3} more text')
    assert result == {"c": 3}


def test_extract_json_invalid_returns_raw():
    result = _extract_json("not json at all")
    assert result == {"raw": "not json at all"}


# ── plan() ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_real_executor_plan_calls_hermes(session):
    executor = RealCommanderExecutor()
    with patch.object(executor, "_call_hermes", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = {
            "content": '{"tasks": [{"title": "T1", "description": "D1"}], '
            '"architect_notes": "Plan notes"}'
        }

        result = await executor.plan(session)

    assert "tasks" in result
    assert len(result["tasks"]) == 1
    assert result["tasks"][0]["title"] == "T1"
    assert result["architect_notes"] == "Plan notes"


@pytest.mark.asyncio
async def test_real_executor_plan_fallback_on_error(session):
    executor = RealCommanderExecutor()
    with patch.object(executor, "_call_hermes", new_callable=AsyncMock) as mock_call:
        mock_call.side_effect = Exception("Connection refused")

        result = await executor.plan(session)

    assert "tasks" in result
    assert len(result["tasks"]) == 1
    assert "fallback" in result.get("architect_notes", "")


# ── implement() ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_real_executor_implement_calls_openclaw(session, task):
    executor = RealCommanderExecutor()
    with patch.object(executor, "_call_openclaw", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = {"content": "def main(): pass"}

        result = await executor.implement(session, task)

    assert result["status"] == "implemented"
    assert "def main" in result["result"]


@pytest.mark.asyncio
async def test_real_executor_implement_detects_question(session, task):
    executor = RealCommanderExecutor()
    with patch.object(executor, "_call_openclaw", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = {
            "content": "QUESTION: Which directory should I use, src/ or lib/?"
        }

        result = await executor.implement(session, task)

    assert result["status"] == "question_pending"
    assert "src/" in result["question"]


# ── review() ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_real_executor_review_approved(session, task):
    executor = RealCommanderExecutor()
    with patch.object(executor, "_call_hermes", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = {
            "content": '{"status": "approved", "comment": "Looks good"}'
        }

        result = await executor.review(session, task)

    assert result["status"] == "approved"
    assert result["comment"] == "Looks good"


@pytest.mark.asyncio
async def test_real_executor_review_rejected(session, task):
    executor = RealCommanderExecutor()
    with patch.object(executor, "_call_hermes", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = {
            "content": '{"status": "rejected", "comment": "Needs tests"}'
        }

        result = await executor.review(session, task)

    assert result["status"] == "rejected"


# ── test() ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_real_executor_test_passed(session, task):
    executor = RealCommanderExecutor()
    with patch.object(executor, "_call_hermes", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = {
            "content": '{"status": "passed", "output": "All 3 tests passed"}'
        }

        result = await executor.test(session, task)

    assert result["status"] == "passed"
    assert "3 tests" in result["output"]


# ── environmental config ───────────────────────────────────

@pytest.mark.asyncio
async def test_real_executor_respects_env_urls(monkeypatch):
    monkeypatch.setenv("HERMES_ADAPTER_URL", "http://custom:9001")
    monkeypatch.setenv("OPENCLAW_ADAPTER_URL", "http://custom:9002")

    # Re-import to pick up env vars
    import importlib
    import commander.real_executor
    importlib.reload(commander.real_executor)
    from commander.real_executor import RealCommanderExecutor as RCE

    executor = RCE()
    assert executor._hermes_url == "http://custom:9001"
    assert executor._openclaw_url == "http://custom:9002"
