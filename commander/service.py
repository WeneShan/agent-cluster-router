"""
Agent Cluster Router — Commander 服务
管理 Commander Session 生命周期，支持 continue 状态推进
"""
from typing import Dict, Optional
from datetime import datetime

from commander.models import CommanderSession, CommanderTask, CommanderState, TaskState
from commander.state_machine import transition, validate_transition
from commander.executor import CommanderExecutor
from commander.fake_executor import FakeCommanderExecutor


class CommanderService:
    """Commander Session 管理器"""

    def __init__(self, executor: Optional[CommanderExecutor] = None):
        self._sessions: Dict[str, CommanderSession] = {}
        self._executor = executor or FakeCommanderExecutor()

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

    # ── v5.4: continue 状态推进 ──────────────────────────────

    async def continue_session(self, session_id: str) -> dict:
        """根据当前状态推进 Commander 会话到下一步

        支持的 10 种状态流转：
          planning → task_dispatched
          task_dispatched → implementing
          implementing → reviewing | question_pending
          question_pending → user_decision_required | implementing
          user_decision_required → implementing
          reviewing → testing | rejected
          testing → accepted | rejected
          rejected → implementing

        Returns:
            {"session_id": ..., "state": ..., "current_task_id": ..., "message": ..., "event": ...}
        """
        session = self._get_or_raise(session_id)
        old_state = session.state

        # 终态不可继续
        if session.state in (CommanderState.ACCEPTED, CommanderState.FAILED):
            raise ValueError(
                f"Session {session_id} is in terminal state '{session.state.value}'"
            )

        # ── PLANNING → TASK_DISPATCHED ──
        if session.state == CommanderState.PLANNING:
            plan_result = await self._executor.plan(session)
            self._apply_plan(session, plan_result)
            self._transit(session, CommanderState.TASK_DISPATCHED)

        # ── TASK_DISPATCHED → IMPLEMENTING ──
        elif session.state == CommanderState.TASK_DISPATCHED:
            task = session.next_task()
            if not task:
                raise ValueError("No pending tasks to implement")
            # Task: PENDING → DISPATCHED → IMPLEMENTING
            validate_transition(task.state, TaskState.DISPATCHED)
            task.state = TaskState.DISPATCHED
            validate_transition(task.state, TaskState.IMPLEMENTING)
            task.state = TaskState.IMPLEMENTING
            task.started_at = datetime.now()
            session.current_task_id = task.id
            self._transit(session, CommanderState.IMPLEMENTING)

        # ── IMPLEMENTING → REVIEWING | QUESTION_PENDING ──
        elif session.state == CommanderState.IMPLEMENTING:
            task = self._current_task(session)
            impl_result = await self._executor.implement(session, task)

            if impl_result.get("status") == "question_pending":
                task.result = impl_result.get("result", "")
                task.question = impl_result.get("question", "")
                validate_transition(task.state, TaskState.QUESTION_PENDING)
                task.state = TaskState.QUESTION_PENDING
                self._transit(session, CommanderState.QUESTION_PENDING)

            elif impl_result.get("status") == "failed":
                task.result = impl_result.get("result", "")
                validate_transition(task.state, TaskState.FAILED)
                task.state = TaskState.FAILED
                task.completed_at = datetime.now()
                self._transit(session, CommanderState.FAILED)

            else:  # "implemented"
                task.result = impl_result.get("result", "")
                validate_transition(task.state, TaskState.REVIEWING)
                task.state = TaskState.REVIEWING
                self._transit(session, CommanderState.REVIEWING)

        # ── QUESTION_PENDING → USER_DECISION_REQUIRED | IMPLEMENTING ──
        elif session.state == CommanderState.QUESTION_PENDING:
            task = self._current_task(session)
            if task.user_decision:
                # 用户已回答 → 继续实现
                validate_transition(task.state, TaskState.IMPLEMENTING)
                task.state = TaskState.IMPLEMENTING
                self._transit(session, CommanderState.IMPLEMENTING)
            else:
                # 等待用户决策
                validate_transition(task.state, TaskState.USER_DECISION_REQUIRED)
                task.state = TaskState.USER_DECISION_REQUIRED
                self._transit(session, CommanderState.USER_DECISION_REQUIRED)

        # ── USER_DECISION_REQUIRED → IMPLEMENTING ──
        elif session.state == CommanderState.USER_DECISION_REQUIRED:
            task = self._current_task(session)
            validate_transition(task.state, TaskState.IMPLEMENTING)
            task.state = TaskState.IMPLEMENTING
            self._transit(session, CommanderState.IMPLEMENTING)

        # ── REVIEWING → TESTING | REJECTED ──
        elif session.state == CommanderState.REVIEWING:
            task = self._current_task(session)
            review_result = await self._executor.review(session, task)

            if review_result.get("status") == "approved":
                task.review_comment = review_result.get("comment", "")
                validate_transition(task.state, TaskState.TESTING)
                task.state = TaskState.TESTING
                self._transit(session, CommanderState.TESTING)

            else:  # rejected
                task.review_comment = review_result.get("comment", "")
                validate_transition(task.state, TaskState.REJECTED)
                task.state = TaskState.REJECTED
                self._transit(session, CommanderState.REJECTED)

        # ── TESTING → ACCEPTED | REJECTED | TASK_DISPATCHED ──
        elif session.state == CommanderState.TESTING:
            task = self._current_task(session)
            test_result = await self._executor.test(session, task)

            if test_result.get("status") == "passed":
                task.test_result = test_result.get("output", "")
                validate_transition(task.state, TaskState.ACCEPTED)
                task.state = TaskState.ACCEPTED
                task.completed_at = datetime.now()

                if session.all_tasks_done():
                    self._transit(session, CommanderState.ACCEPTED)
                else:
                    # 还有更多任务 → 回到分发状态
                    session.current_task_id = None
                    self._transit(session, CommanderState.TASK_DISPATCHED)

            else:  # failed
                task.test_result = test_result.get("output", "")
                validate_transition(task.state, TaskState.REJECTED)
                task.state = TaskState.REJECTED
                task.completed_at = datetime.now()
                self._transit(session, CommanderState.REJECTED)

        # ── REJECTED → IMPLEMENTING ──
        elif session.state == CommanderState.REJECTED:
            task = self._current_task(session)
            validate_transition(task.state, TaskState.IMPLEMENTING)
            task.state = TaskState.IMPLEMENTING
            task.started_at = datetime.now()
            self._transit(session, CommanderState.IMPLEMENTING)

        # 更新 session 时间戳
        session.updated_at = datetime.now()

        return {
            "session_id": session.id,
            "state": session.state.value,
            "current_task_id": session.current_task_id,
            "message": "Commander session advanced.",
            "event": {
                "from": old_state.value,
                "to": session.state.value,
            },
        }

    # ── 内部辅助方法 ──────────────────────────────────────

    def _apply_plan(self, session: CommanderSession, plan_result: dict):
        """将 executor.plan() 的结果应用到 session"""
        tasks_data = plan_result.get("tasks", [])
        for i, tdata in enumerate(tasks_data):
            criteria = [
                {"description": c.get("description", "")}
                for c in tdata.get("acceptance_criteria", [])
            ]
            task = CommanderTask(
                id=f"{session.id}_t{i + 1}",
                title=tdata.get("title", f"Task {i + 1}"),
                description=tdata.get("description", ""),
                state=TaskState.PENDING,
                acceptance_criteria=criteria,
            )
            session.tasks.append(task)

        if plan_result.get("architect_notes"):
            session.architect_notes = plan_result["architect_notes"]

    def _current_task(self, session: CommanderSession) -> CommanderTask:
        """获取当前正在处理的任务"""
        if not session.current_task_id:
            raise ValueError("No current task in session")
        task = next(
            (t for t in session.tasks if t.id == session.current_task_id), None
        )
        if not task:
            raise ValueError(
                f"Current task {session.current_task_id} not found in session"
            )
        return task

    def _transit(self, session: CommanderSession, target: CommanderState):
        """执行状态流转（带验证）"""
        validate_transition(session.state, target)
        session.state = target

    def _get_or_raise(self, session_id: str) -> CommanderSession:
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        return session


# 全局单例
commander_service = CommanderService()
