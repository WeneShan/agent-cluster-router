"""Commander API 集成测试 — 验证 REST 端点行为"""
import pytest
from fastapi.testclient import TestClient

from router.server import app

client = TestClient(app)


# ============================================================
# POST /commander/sessions — 创建会话
# ============================================================

def test_create_commander_session():
    resp = client.post(
        "/commander/sessions",
        json={
            "user_id": "user_test",
            "goal": "帮我做一个博客系统",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "user_test"
    assert data["goal"] == "帮我做一个博客系统"
    assert "id" in data
    assert data["state"] == "planning"
    assert data["tasks"] == []


# ============================================================
# GET /commander/sessions/{id} — 查询会话
# ============================================================

def test_get_commander_session():
    create_resp = client.post(
        "/commander/sessions",
        json={
            "user_id": "user_test_get",
            "goal": "测试查询 session",
        },
    )
    session_id = create_resp.json()["id"]

    get_resp = client.get(
        f"/commander/sessions/{session_id}",
        params={"user_id": "user_test_get"},
    )
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == session_id
    assert data["goal"] == "测试查询 session"


# ============================================================
# GET /commander/sessions/{id}/tasks — 查询任务列表
# ============================================================

def test_get_commander_tasks():
    create_resp = client.post(
        "/commander/sessions",
        json={
            "user_id": "user_test_tasks",
            "goal": "测试任务列表",
        },
    )
    session_id = create_resp.json()["id"]

    tasks_resp = client.get(
        f"/commander/sessions/{session_id}/tasks",
        params={"user_id": "user_test_tasks"},
    )
    assert tasks_resp.status_code == 200
    data = tasks_resp.json()
    assert data["session_id"] == session_id
    assert data["tasks"] == []


# ============================================================
# POST /commander/sessions/{id}/answer — 提交用户决策
# ============================================================

def test_answer_question():
    """创建 session → 手动推入一个待决策任务 → answer 回到 implementing"""
    from commander.service import commander_service
    from commander.models import CommanderTask, TaskState

    session = commander_service.create_session(user_id="user_answer", goal="test answer flow")

    # 手动添加一个待决策任务
    task = CommanderTask(
        id="task_001",
        title="choose database",
        description="MySQL or Postgres?",
        state=TaskState.USER_DECISION_REQUIRED,
    )
    commander_service.add_task(session.id, task)

    # 提交回答
    resp = client.post(
        f"/commander/sessions/{session.id}/answer",
        json={
            "user_id": "user_answer",
            "question_id": "task_001",
            "answer": "MySQL",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == session.id

    # 验证任务状态已更新
    updated_task = next(t for t in data["tasks"] if t["id"] == "task_001")
    assert updated_task["state"] == "implementing"
    assert updated_task["user_decision"] == "MySQL"


# ============================================================
# 404 — 不存在的 session
# ============================================================

def test_get_missing_commander_session_returns_404():
    resp = client.get(
        "/commander/sessions/not_exist",
        params={"user_id": "user_test"},
    )
    assert resp.status_code == 404


def test_get_missing_commander_tasks_returns_404():
    resp = client.get(
        "/commander/sessions/not_exist/tasks",
        params={"user_id": "user_test"},
    )
    assert resp.status_code == 404


def test_answer_missing_session_returns_404():
    resp = client.post(
        "/commander/sessions/not_exist/answer",
        json={
            "user_id": "user_test",
            "answer": "something",
        },
    )
    assert resp.status_code == 404


# ============================================================
# 400 — 无待决策问题时 answer
# ============================================================

def test_answer_without_pending_question_returns_400():
    create_resp = client.post(
        "/commander/sessions",
        json={
            "user_id": "user_no_question",
            "goal": "no questions here",
        },
    )
    session_id = create_resp.json()["id"]

    resp = client.post(
        f"/commander/sessions/{session_id}/answer",
        json={
            "user_id": "user_no_question",
            "answer": "nothing to answer",
        },
    )
    assert resp.status_code == 400


# ============================================================
# user_id 隔离 — 不能查看别人的 session
# ============================================================

def test_user_isolation():
    """user_A 创建的 session，user_B 不能查看"""
    create_resp = client.post(
        "/commander/sessions",
        json={
            "user_id": "user_A",
            "goal": "A's secret plan",
        },
    )
    session_id = create_resp.json()["id"]

    # user_A 可查看
    resp_a = client.get(
        f"/commander/sessions/{session_id}",
        params={"user_id": "user_A"},
    )
    assert resp_a.status_code == 200

    # user_B 不可查看
    resp_b = client.get(
        f"/commander/sessions/{session_id}",
        params={"user_id": "user_B"},
    )
    assert resp_b.status_code == 404
