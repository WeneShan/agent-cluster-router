"""Commander 状态机单元测试 — 验证合法与非法状态流转"""
import pytest

from commander.models import CommanderState, TaskState
from commander.state_machine import (
    transition,
    validate_transition,
    can_transition,
    is_terminal,
)


# ============================================================
# Session 级别 — 合法状态流转
# ============================================================

def test_session_transition_planning_to_task_dispatched():
    result = transition(CommanderState.PLANNING, CommanderState.TASK_DISPATCHED)
    assert result == CommanderState.TASK_DISPATCHED


def test_session_transition_task_dispatched_to_implementing():
    result = transition(CommanderState.TASK_DISPATCHED, CommanderState.IMPLEMENTING)
    assert result == CommanderState.IMPLEMENTING


def test_session_transition_implementing_to_question_pending():
    result = transition(CommanderState.IMPLEMENTING, CommanderState.QUESTION_PENDING)
    assert result == CommanderState.QUESTION_PENDING


def test_session_transition_question_pending_to_user_decision():
    result = transition(CommanderState.QUESTION_PENDING, CommanderState.USER_DECISION_REQUIRED)
    assert result == CommanderState.USER_DECISION_REQUIRED


def test_session_transition_user_decision_to_implementing():
    result = transition(CommanderState.USER_DECISION_REQUIRED, CommanderState.IMPLEMENTING)
    assert result == CommanderState.IMPLEMENTING


def test_session_transition_implementing_to_reviewing():
    result = transition(CommanderState.IMPLEMENTING, CommanderState.REVIEWING)
    assert result == CommanderState.REVIEWING


def test_session_transition_reviewing_to_testing():
    result = transition(CommanderState.REVIEWING, CommanderState.TESTING)
    assert result == CommanderState.TESTING


def test_session_transition_testing_to_accepted():
    result = transition(CommanderState.TESTING, CommanderState.ACCEPTED)
    assert result == CommanderState.ACCEPTED


def test_session_transition_testing_to_rejected():
    result = transition(CommanderState.TESTING, CommanderState.REJECTED)
    assert result == CommanderState.REJECTED


def test_session_transition_rejected_to_implementing():
    result = transition(CommanderState.REJECTED, CommanderState.IMPLEMENTING)
    assert result == CommanderState.IMPLEMENTING


# ============================================================
# Task 级别 — 合法状态流转
# ============================================================

def test_task_transition_pending_to_dispatched():
    result = transition(TaskState.PENDING, TaskState.DISPATCHED)
    assert result == TaskState.DISPATCHED


def test_task_transition_dispatched_to_implementing():
    result = transition(TaskState.DISPATCHED, TaskState.IMPLEMENTING)
    assert result == TaskState.IMPLEMENTING


def test_task_transition_implementing_to_reviewing():
    result = transition(TaskState.IMPLEMENTING, TaskState.REVIEWING)
    assert result == TaskState.REVIEWING


def test_task_transition_reviewing_to_accepted():
    result = transition(TaskState.REVIEWING, TaskState.ACCEPTED)
    assert result == TaskState.ACCEPTED


def test_task_transition_rejected_to_implementing():
    result = transition(TaskState.REJECTED, TaskState.IMPLEMENTING)
    assert result == TaskState.IMPLEMENTING


# ============================================================
# 非法状态流转 — 应抛出 ValueError
# ============================================================

def test_invalid_transition_planning_to_accepted():
    with pytest.raises(ValueError):
        transition(CommanderState.PLANNING, CommanderState.ACCEPTED)


def test_invalid_transition_accepted_to_implementing():
    with pytest.raises(ValueError):
        transition(CommanderState.ACCEPTED, CommanderState.IMPLEMENTING)


def test_invalid_transition_failed_to_implementing():
    with pytest.raises(ValueError):
        transition(CommanderState.FAILED, CommanderState.IMPLEMENTING)


def test_invalid_task_transition_pending_to_accepted():
    with pytest.raises(ValueError):
        transition(TaskState.PENDING, TaskState.ACCEPTED)


def test_invalid_task_transition_accepted_to_implementing():
    with pytest.raises(ValueError):
        transition(TaskState.ACCEPTED, TaskState.IMPLEMENTING)


# ============================================================
# can_transition — 安全检查
# ============================================================

def test_can_transition_allows_valid():
    assert can_transition(CommanderState.PLANNING, CommanderState.TASK_DISPATCHED) is True
    assert can_transition(CommanderState.IMPLEMENTING, CommanderState.REVIEWING) is True


def test_can_transition_rejects_invalid():
    assert can_transition(CommanderState.PLANNING, CommanderState.ACCEPTED) is False
    assert can_transition(CommanderState.ACCEPTED, CommanderState.IMPLEMENTING) is False


# ============================================================
# is_terminal — 终态检查
# ============================================================

def test_is_terminal_session():
    assert is_terminal(CommanderState.ACCEPTED) is True
    assert is_terminal(CommanderState.FAILED) is True
    assert is_terminal(CommanderState.PLANNING) is False
    assert is_terminal(CommanderState.IMPLEMENTING) is False


def test_is_terminal_task():
    assert is_terminal(TaskState.ACCEPTED) is True
    assert is_terminal(TaskState.FAILED) is True
    assert is_terminal(TaskState.PENDING) is False
    assert is_terminal(TaskState.IMPLEMENTING) is False


# ============================================================
# validate_transition — 不抛即通过
# ============================================================

def test_validate_transition_passes_valid():
    # Should not raise
    validate_transition(CommanderState.PLANNING, CommanderState.TASK_DISPATCHED)
    validate_transition(CommanderState.REVIEWING, CommanderState.TESTING)


def test_validate_transition_raises_invalid():
    with pytest.raises(ValueError):
        validate_transition(CommanderState.ACCEPTED, CommanderState.PLANNING)
