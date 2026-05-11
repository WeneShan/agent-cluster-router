"""
Agent Cluster Router — Commander 状态机
定义状态流转规则和验证
"""
from commander.models import CommanderState, TaskState


# --- Session 级别状态流转 ---
SESSION_TRANSITIONS: dict[CommanderState, list[CommanderState]] = {
    CommanderState.PLANNING: [
        CommanderState.TASK_DISPATCHED,
        CommanderState.FAILED,
    ],
    CommanderState.TASK_DISPATCHED: [
        CommanderState.IMPLEMENTING,
        CommanderState.FAILED,
    ],
    CommanderState.IMPLEMENTING: [
        CommanderState.QUESTION_PENDING,
        CommanderState.REVIEWING,
        CommanderState.FAILED,
    ],
    CommanderState.QUESTION_PENDING: [
        CommanderState.USER_DECISION_REQUIRED,
        CommanderState.IMPLEMENTING,
    ],
    CommanderState.USER_DECISION_REQUIRED: [
        CommanderState.IMPLEMENTING,
        CommanderState.FAILED,
    ],
    CommanderState.REVIEWING: [
        CommanderState.TESTING,
        CommanderState.REJECTED,
        CommanderState.ACCEPTED,
    ],
    CommanderState.TESTING: [
        CommanderState.ACCEPTED,
        CommanderState.REJECTED,
        CommanderState.FAILED,
    ],
    CommanderState.ACCEPTED: [],         # 终态
    CommanderState.REJECTED: [
        CommanderState.IMPLEMENTING,
        CommanderState.FAILED,
    ],
    CommanderState.FAILED: [],           # 终态
}


# --- Task 级别状态流转 ---
TASK_TRANSITIONS: dict[TaskState, list[TaskState]] = {
    TaskState.PENDING: [
        TaskState.DISPATCHED,
        TaskState.FAILED,
    ],
    TaskState.DISPATCHED: [
        TaskState.IMPLEMENTING,
        TaskState.FAILED,
    ],
    TaskState.IMPLEMENTING: [
        TaskState.QUESTION_PENDING,
        TaskState.REVIEWING,
        TaskState.FAILED,
    ],
    TaskState.QUESTION_PENDING: [
        TaskState.USER_DECISION_REQUIRED,
        TaskState.IMPLEMENTING,
    ],
    TaskState.USER_DECISION_REQUIRED: [
        TaskState.IMPLEMENTING,
        TaskState.FAILED,
    ],
    TaskState.REVIEWING: [
        TaskState.TESTING,
        TaskState.REJECTED,
        TaskState.ACCEPTED,
    ],
    TaskState.TESTING: [
        TaskState.ACCEPTED,
        TaskState.REJECTED,
        TaskState.FAILED,
    ],
    TaskState.ACCEPTED: [],              # 终态
    TaskState.REJECTED: [
        TaskState.IMPLEMENTING,
        TaskState.FAILED,
    ],
    TaskState.FAILED: [],                # 终态
}


def validate_transition(current: CommanderState | TaskState,
                         target: CommanderState | TaskState) -> None:
    """验证状态流转是否合法
    
    Raises:
        ValueError: 非法状态流转
    """
    if isinstance(current, CommanderState):
        allowed = SESSION_TRANSITIONS.get(current, [])
    else:
        allowed = TASK_TRANSITIONS.get(current, [])

    if target not in allowed:
        raise ValueError(
            f"Invalid transition: {current.value} -> {target.value}. "
            f"Allowed: {[s.value for s in allowed]}"
        )


def transition(current, target):
    """执行状态流转（带验证）
    
    Returns:
        目标状态
    Raises:
        ValueError: 非法流转
    """
    validate_transition(current, target)
    return target


def can_transition(current, target) -> bool:
    """检查是否可以流转到目标状态"""
    if isinstance(current, CommanderState):
        allowed = SESSION_TRANSITIONS.get(current, [])
    else:
        allowed = TASK_TRANSITIONS.get(current, [])
    return target in allowed


def is_terminal(state: CommanderState | TaskState) -> bool:
    """检查是否为终态"""
    if isinstance(state, CommanderState):
        return state in (CommanderState.ACCEPTED, CommanderState.FAILED)
    return state in (TaskState.ACCEPTED, TaskState.FAILED)
