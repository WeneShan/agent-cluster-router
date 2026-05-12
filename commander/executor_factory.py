"""
Agent Cluster Router — Executor Factory
根据环境变量选择 Commander Executor（fake / real）
"""
import os
from typing import Optional

from commander.executor import CommanderExecutor
from commander.fake_executor import FakeCommanderExecutor


def get_commander_executor(mode: Optional[str] = None) -> CommanderExecutor:
    """获取 CommanderExecutor 实例

    优先级：
      1. 显式传入 mode 参数
      2. 环境变量 COMMANDER_EXECUTOR（默认 "fake"）

    mode='fake'  → FakeCommanderExecutor（默认，无 AI 依赖）
    mode='real'  → RealCommanderExecutor（调用 Hermes/OpenClaw）
    """
    if mode is None:
        mode = os.getenv("COMMANDER_EXECUTOR", "fake").lower().strip()

    if mode == "real":
        from commander.real_executor import RealCommanderExecutor

        return RealCommanderExecutor()

    return FakeCommanderExecutor()
