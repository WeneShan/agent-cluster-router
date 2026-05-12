"""Security Policy — 定义安全规则和匹配引擎"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
import re


class SecurityAction(str, Enum):
    ALLOW = "allow"
    CONFIRM = "confirmation_required"
    REVIEW = "security_review"
    BLOCK = "blocked"


@dataclass
class SecurityRule:
    name: str
    patterns: List[str]
    action: SecurityAction
    reason: str


SECURITY_RULES = [
    SecurityRule(
        name="credential_theft",
        patterns=[
            r"api key",
            r"token",
            r"secret",
            r"steal.*key",
            r"窃取.*密钥",
            r"获取.*token",
            r"偷.*api",
            r"别人的.*key",
            r"how to get.*api key",
        ],
        action=SecurityAction.REVIEW,
        reason="Request involves credentials or secrets.",
    ),
    SecurityRule(
        name="bypass_security",
        patterns=[
            r"bypass.*firewall",
            r"绕过.*防火墙",
            r"绕过.*认证",
            r"绕过.*安全",
            r"disable.*security",
            r"hack into",
            r"hack.*server",
            r"入侵",
            r"破解.*密码",
        ],
        action=SecurityAction.BLOCK,
        reason="Request attempts to bypass security controls.",
    ),
    SecurityRule(
        name="destructive_command",
        patterns=[
            r"rm\s+-rf\s+/",
            r"drop\s+database",
            r"truncate\s+table",
            r"删除.*数据库",
            r"清空.*生产",
            r"delete.*production",
            r"生产环境.*删除",
            r"部署.*命令",
            r"exec.*deploy",
        ],
        action=SecurityAction.CONFIRM,
        reason="Request contains potentially destructive operations.",
    ),
    SecurityRule(
        name="harmful_code",
        patterns=[
            r"virus",
            r"malware",
            r"ransomware",
            r"木马",
            r"病毒",
            r"恶意.*代码",
            r"write.*exploit",
            r"编写.*漏洞",
        ],
        action=SecurityAction.BLOCK,
        reason="Request involves harmful or malicious code generation.",
    ),
    SecurityRule(
        name="saas_without_review",
        patterns=[
            r"build.*me.*a.*saas",
            r"给我.*建.*一个.*saas",
            r"build.*saas.*product",
        ],
        action=SecurityAction.REVIEW,
        reason="Large-scale SaaS product request requires security review.",
    ),
]


def match_security_policy(text: str) -> Optional[SecurityRule]:
    """扫描用户输入，返回第一个匹配的安全规则。"""
    if not text:
        return None
    normalized = text.lower()
    for rule in SECURITY_RULES:
        for pattern in rule.patterns:
            if re.search(pattern, normalized, re.IGNORECASE):
                return rule
    return None
