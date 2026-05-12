"""Commander Executor Factory 单元测试"""
import os
import pytest

pytestmark = pytest.mark.unit

from commander.executor_factory import get_commander_executor
from commander.fake_executor import FakeCommanderExecutor


def test_factory_default_is_fake():
    """默认模式返回 FakeCommanderExecutor"""
    executor = get_commander_executor()
    assert isinstance(executor, FakeCommanderExecutor)


def test_factory_explicit_fake():
    """显式 'fake' 返回 FakeCommanderExecutor"""
    executor = get_commander_executor(mode="fake")
    assert isinstance(executor, FakeCommanderExecutor)


def test_factory_fake_via_env(monkeypatch):
    """环境变量 COMMANDER_EXECUTOR=fake 返回 FakeCommanderExecutor"""
    monkeypatch.setenv("COMMANDER_EXECUTOR", "fake")
    executor = get_commander_executor()
    assert isinstance(executor, FakeCommanderExecutor)


def test_factory_explicit_mode_overrides_env(monkeypatch):
    """显式 mode 参数覆盖环境变量"""
    monkeypatch.setenv("COMMANDER_EXECUTOR", "real")
    executor = get_commander_executor(mode="fake")
    assert isinstance(executor, FakeCommanderExecutor)


def test_factory_default_env_not_set(monkeypatch):
    """未设置 COMMANDER_EXECUTOR 时默认 fake"""
    monkeypatch.delenv("COMMANDER_EXECUTOR", raising=False)
    executor = get_commander_executor()
    assert isinstance(executor, FakeCommanderExecutor)


def test_factory_case_insensitive(monkeypatch):
    """环境变量大小写不敏感"""
    monkeypatch.setenv("COMMANDER_EXECUTOR", "FAKE")
    executor = get_commander_executor()
    assert isinstance(executor, FakeCommanderExecutor)


def test_factory_whitespace_handling(monkeypatch):
    """环境变量有前后空格也能处理"""
    monkeypatch.setenv("COMMANDER_EXECUTOR", "  fake  ")
    executor = get_commander_executor()
    assert isinstance(executor, FakeCommanderExecutor)
