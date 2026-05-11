"""
Agent Cluster Router — Commander 状态机模型
定义 Commander Session 和 Task 的状态、数据结构
"""
from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CommanderState(str, Enum):
    """Commander Session 整体状态"""
    PLANNING = "planning"                       # Hermes 正在规划
    TASK_DISPATCHED = "task_dispatched"          # 任务已分发
    IMPLEMENTING = "implementing"                # OpenClaw 正在实现
    QUESTION_PENDING = "question_pending"        # OpenClaw 提问待处理
    USER_DECISION_REQUIRED = "user_decision_required"  # 需要用户决策
    REVIEWING = "reviewing"                      # Hermes 正在审查
    TESTING = "testing"                          # 自动测试中
    ACCEPTED = "accepted"                        # 全部通过
    REJECTED = "rejected"                        # 审查/测试不通过
    FAILED = "failed"                            # 执行失败


class TaskState(str, Enum):
    """单个任务状态"""
    PENDING = "pending"
    DISPATCHED = "dispatched"
    IMPLEMENTING = "implementing"
    QUESTION_PENDING = "question_pending"
    USER_DECISION_REQUIRED = "user_decision_required"
    REVIEWING = "reviewing"
    TESTING = "testing"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    FAILED = "failed"


class QuestionCategory(str, Enum):
    """OpenClaw 提问分类"""
    FILENAME = "filename"
    CODE_STYLE = "code_style"
    TYPE_HINT = "type_hint"
    FORMATTING = "formatting"
    DIRECTORY_STRUCTURE = "directory_structure"
    MINOR_DETAIL = "minor_implementation_detail"
    DATABASE_CHOICE = "database_choice"
    AUTH_STRATEGY = "authentication_strategy"
    DEPLOYMENT_TARGET = "deployment_target"
    PAYMENT_PROVIDER = "payment_provider"
    ARCHITECTURE_SPLIT = "architecture_split"
    DATA_PRIVACY = "data_privacy"
    BUSINESS_RULE = "business_rule"


class AcceptanceCriteria(BaseModel):
    """任务验收标准"""
    description: str
    check: str = ""  # shell 命令或 Python 表达式


class CommanderTask(BaseModel):
    """Commander 子任务"""
    id: str
    title: str
    description: str = ""
    state: TaskState = TaskState.PENDING
    assigned_to: str = "openclaw"
    acceptance_criteria: List[AcceptanceCriteria] = []
    result: Optional[str] = None
    question: Optional[str] = None
    question_category: Optional[QuestionCategory] = None
    user_decision: Optional[str] = None
    review_comment: Optional[str] = None
    test_result: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class CommanderSession(BaseModel):
    """Commander 协作会话
    
    一个 Commander Session 包含：
    - 用户提出的目标
    - Hermes 分解的任务列表
    - 每个任务的状态追踪
    """
    id: str = Field(default_factory=lambda: f"cmd_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    user_id: str = "default"
    goal: str
    state: CommanderState = CommanderState.PLANNING
    tasks: List[CommanderTask] = []
    current_task_id: Optional[str] = None
    architect_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def next_task(self) -> Optional[CommanderTask]:
        """获取下一个待处理任务"""
        for task in self.tasks:
            if task.state in (TaskState.PENDING, TaskState.REJECTED):
                return task
        return None

    def all_tasks_done(self) -> bool:
        """所有任务是否都已完成"""
        return all(
            t.state == TaskState.ACCEPTED
            for t in self.tasks
        )
