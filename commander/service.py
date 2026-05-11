"""
Agent Cluster Router — Commander 服务
管理 Commander Session 生命周期
"""
from typing import Dict, Optional
from commander.models import CommanderSession, CommanderTask, CommanderState, TaskState
from commander.state_machine import transition, validate_transition


class CommanderService:
    """Commander Session 管理器"""

    def __init__(self):
        self._sessions: Dict[str, CommanderSession] = {}

    def create_session(self, user_id: str, goal: str) -> CommanderSession:
        """创建新的 Commander 会话"""
        session = CommanderSession(user_id=user_id, goal=goal)
        self._sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> Optional[CommanderSession]:
        """获取会话"""
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[dict]:
        """列出所有会话"""
        return [
            {
                "id": s.id,
                "user_id": s.user_id,
                "goal": s.goal[:100],
                "state": s.state.value,
                "tasks_total": len(s.tasks),
                "tasks_done": sum(1 for t in s.tasks if t.state == TaskState.ACCEPTED),
            }
            for s in self._sessions.values()
        ]

    def transition_session(self, session_id: str, target: CommanderState) -> CommanderSession:
        """流转 Session 状态"""
        session = self._get_or_raise(session_id)
        validate_transition(session.state, target)
        session.state = target
        return session

    def add_task(self, session_id: str, task: CommanderTask) -> CommanderSession:
        """向 Session 添加任务"""
        session = self._get_or_raise(session_id)
        session.tasks.append(task)
        return session

    def transition_task(self, session_id: str, task_id: str, target: TaskState) -> CommanderTask:
        """流转 Task 状态"""
        session = self._get_or_raise(session_id)
        task = next((t for t in session.tasks if t.id == task_id), None)
        if not task:
            raise ValueError(f"Task {task_id} not found in session {session_id}")
        validate_transition(task.state, target)
        task.state = target
        return task

    def delete_session(self, session_id: str):
        """删除会话"""
        self._sessions.pop(session_id, None)

    def _get_or_raise(self, session_id: str) -> CommanderSession:
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        return session


# 全局单例
commander_service = CommanderService()
