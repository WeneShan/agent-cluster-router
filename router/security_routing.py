"""Security-aware Routing — L0 安全路由层"""
from dataclasses import dataclass
from typing import Optional

from router.security_policy import (
    match_security_policy,
    SecurityRule,
    SecurityAction,
)


@dataclass
class SecurityRoutingResult:
    """安全路由决策结果"""
    matched: bool
    rule: Optional[SecurityRule] = None
    action: Optional[SecurityAction] = None
    selected_backend: Optional[str] = None
    decision_layer: str = "L0_SECURITY"
    reason: str = ""

    @classmethod
    def no_match(cls) -> "SecurityRoutingResult":
        return cls(matched=False)

    @classmethod
    def from_rule(cls, rule: SecurityRule) -> "SecurityRoutingResult":
        backend = None
        if rule.action == SecurityAction.BLOCK:
            backend = None  # blocked — 不路由到任何后端
        elif rule.action in (SecurityAction.CONFIRM, SecurityAction.REVIEW):
            backend = "hermes"  # 需要确认或审查时，路由到 Hermes（安全审查能力更强）

        return cls(
            matched=True,
            rule=rule,
            action=rule.action,
            selected_backend=backend,
            reason=rule.reason,
        )


def evaluate_security(text: str) -> SecurityRoutingResult:
    """对用户输入执行安全策略检查（L0 层）"""
    rule = match_security_policy(text)
    if rule:
        return SecurityRoutingResult.from_rule(rule)
    return SecurityRoutingResult.no_match()
