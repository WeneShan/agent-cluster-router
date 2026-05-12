"""Commander REST API — exposes Commander session lifecycle via FastAPI"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from commander.service import CommanderService, commander_service
from commander.store import commander_store
from commander.models import TaskState

router = APIRouter(prefix="/commander", tags=["commander"])

service = commander_service  # 使用全局单例


class CreateCommanderSessionRequest(BaseModel):
    user_id: str
    goal: str


class AnswerRequest(BaseModel):
    user_id: str
    question_id: Optional[str] = None
    answer: str


class ContinueRequest(BaseModel):
    user_id: str


@router.post("/sessions")
async def create_session(req: CreateCommanderSessionRequest):
    """创建新的 Commander 协作会话"""
    session = service.create_session(
        user_id=req.user_id,
        goal=req.goal,
    )
    return session.model_dump()


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, user_id: str):
    """查询 Commander 会话详情"""
    session = service.get_session(session_id)

    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Commander session not found")

    return session.model_dump()


@router.get("/sessions/{session_id}/tasks")
async def get_tasks(session_id: str, user_id: str):
    """查询 Commander 会话的任务列表"""
    session = service.get_session(session_id)

    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Commander session not found")

    return {
        "session_id": session.id,
        "tasks": [t.model_dump() for t in session.tasks],
    }


@router.post("/sessions/{session_id}/answer")
async def answer_question(session_id: str, req: AnswerRequest):
    """提交用户对 Commander 提问的回答"""
    session = service.get_session(session_id)

    if not session or session.user_id != req.user_id:
        raise HTTPException(status_code=404, detail="Commander session not found")

    try:
        # 找到当前待决策的任务并应用用户回答
        task = next(
            (t for t in session.tasks
             if t.state in (TaskState.QUESTION_PENDING, TaskState.USER_DECISION_REQUIRED)),
            None,
        )
        if not task:
            raise ValueError("No pending question to answer")

        task.user_decision = req.answer
        service.transition_task(session_id, task.id, "implementing")
        return session.model_dump()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/continue")
async def continue_session(session_id: str, req: ContinueRequest):
    """推进 Commander 会话到下一个状态

    根据当前 session 状态自动决策下一步：
      planning → task_dispatched
      task_dispatched → implementing
      implementing → reviewing | question_pending
      question_pending → user_decision_required | implementing
      user_decision_required → implementing
      reviewing → testing | rejected
      testing → accepted | rejected
      rejected → implementing
    """
    session = service.get_session(session_id)

    if not session or session.user_id != req.user_id:
        raise HTTPException(status_code=404, detail="Commander session not found")

    try:
        result = await service.continue_session(session_id)
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
